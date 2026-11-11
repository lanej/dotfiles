#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["grpcio-tools==1.76.0"]
# ///
"""Generate the full pinned Zellij protobuf contract and reference messages for Lua."""
import argparse
import json
from pathlib import Path
import re
import tempfile
import urllib.request

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from grpc_tools import protoc

ROOT = Path(__file__).resolve().parents[1]
FILES = ("common_types.proto", "client_to_server.proto", "server_to_client.proto",
         "app_control.proto", "pane_mirror.proto")
KINDS = {number: name.lower().removeprefix("type_")
         for name, number in descriptor_pb2.FieldDescriptorProto.Type.items()}


def lua(value):
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{key} = {lua(item)}" for key, item in value.items()) + " }"
    return str(value)


def native(message):
    def scalar(field, value):
        if field.type == field.TYPE_MESSAGE:
            return native(value)
        if field.type == field.TYPE_BYTES:
            return {"$bytes": value.hex()}
        if field.type in (field.TYPE_INT64, field.TYPE_UINT64, field.TYPE_SINT64, field.TYPE_FIXED64, field.TYPE_SFIXED64):
            return str(value)
        return value
    result = {}
    for field, value in message.ListFields():
        if field.message_type and field.message_type.GetOptions().map_entry:
            value_field = field.message_type.fields_by_name["value"]
            result[field.name] = {str(key).lower() if isinstance(key, bool) else str(key): scalar(value_field, item)
                                  for key, item in value.items()}
        elif field.is_repeated:
            result[field.name] = [scalar(field, item) for item in value]
        else:
            result[field.name] = scalar(field, value)
    return result


def fixtures(pool, names):
    samples = {"float": 1.5, "int32": -2147483648, "uint64": 18446744073709551615,
               "bool": True, "string": "Unicode 界\n", "bytes": b"\x00\xffliteral", "uint32": 4294967295}
    chosen, examples = set(), []
    def example(descriptor, field, sample):
        message = message_factory.GetMessageClass(descriptor)()
        if field.is_repeated:
            getattr(message, field.name).extend([sample, sample])
        else:
            setattr(message, field.name, sample)
        examples.append(message)
    for name in sorted(names):
        descriptor = pool.FindMessageTypeByName(name)
        if descriptor.GetOptions().map_entry:
            continue
        for field in descriptor.fields:
            kind = KINDS[field.type]
            if kind == "message":
                key_field, value_field = field.message_type.fields if field.message_type.GetOptions().map_entry else (None, None)
                category = ("map", key_field.type, value_field.type) if key_field else "empty-message"
                if category not in chosen:
                    message = message_factory.GetMessageClass(descriptor)()
                    if key_field:
                        key = "key" if key_field.type == key_field.TYPE_STRING else True if key_field.type == key_field.TYPE_BOOL else 1
                        if value_field.type == value_field.TYPE_MESSAGE:
                            getattr(message, field.name)[key].SetInParent()
                        else:
                            sample = value_field.enum_type.values[-1].number if value_field.enum_type else samples[KINDS[value_field.type]]
                            getattr(message, field.name)[key] = sample
                    elif not field.is_repeated:
                        getattr(message, field.name).SetInParent()
                    else:
                        continue
                    examples.append(message)
                    chosen.add(category)
                continue
            sample = field.enum_type.values[-1].number if kind == "enum" else samples[kind]
            category = (kind, field.is_repeated)
            if category not in chosen:
                example(descriptor, field, sample)
                chosen.add(category)
            if field.containing_oneof and ("oneof-default", kind) not in chosen:
                default = field.default_value
                if kind == "enum":
                    default = field.enum_type.values[0].number
                example(descriptor, field, default)
                chosen.add(("oneof-default", kind))
    client = message_factory.GetMessageClass(pool.FindMessageTypeByName("client_server_contract.ClientToServerMsg"))
    first, second = client(), client()
    first.action.terminal_id = 42
    first.action.action.move_focus.direction = 2
    second.action.client_id = 7
    merge_bytes = first.SerializeToString() + second.SerializeToString()
    merged = client.FromString(merge_bytes)
    examples.extend([first, merged])
    empty = client()
    empty.action.action.list_clients.SetInParent()
    examples.append(empty)
    exited = client()
    exited.client_exited.SetInParent()
    replace_bytes = first.SerializeToString() + exited.SerializeToString()
    examples.append(client.FromString(replace_bytes))
    detach = message_factory.GetMessageClass(pool.FindMessageTypeByName("client_server_contract.DetachSessionMsg"))
    unpacked_bytes = b"\x08\x01\x08\x02"
    unpacked = detach.FromString(unpacked_bytes)
    examples.append(unpacked)
    result = [{"type": message.DESCRIPTOR.full_name, "value": native(message),
               "hex": message.SerializeToString(deterministic=True).hex()} for message in examples]
    for message, raw in ((merged, merge_bytes), (examples[-2], replace_bytes), (unpacked, unpacked_bytes)):
        result.append({"type": message.DESCRIPTOR.full_name, "value": native(message),
                       "hex": raw.hex(), "encode_hex": message.SerializeToString(deterministic=True).hex()})
    return result



def generate():
    revision = re.search(r"^zellij_revision=([a-f0-9]+)$", (ROOT / "scripts/install-zellij").read_text(), re.M)[1]
    with tempfile.TemporaryDirectory(prefix="zellij-lua-proto-") as directory:
        work = Path(directory)
        for name in FILES:
            url = f"https://raw.githubusercontent.com/lanej/zellij/{revision}/zellij-utils/src/client_server_contract/{name}"
            with urllib.request.urlopen(url, timeout=30) as response:
                (work / name).write_bytes(response.read())
        descriptor = work / "contract.pb"
        if protoc.main(["protoc", f"-I{work}", f"--descriptor_set_out={descriptor}", "--include_imports",
                        *[str(work / name) for name in FILES]]) != 0:
            raise SystemExit("Cannot compile the pinned Zellij protobuf contract")
        descriptors = descriptor_pb2.FileDescriptorSet.FromString(descriptor.read_bytes())
    messages, enums = {}, {}
    def walk(prefix, message):
        name = prefix + "." + message.name
        messages[name] = message
        for nested in message.nested_type:
            walk(name, nested)
        for enum in message.enum_type:
            enums[name + "." + enum.name] = enum
    pool = descriptor_pool.DescriptorPool()
    for file in descriptors.file:
        pool.Add(file)
        for message in file.message_type:
            walk(file.package, message)
        for enum in file.enum_type:
            enums[file.package + "." + enum.name] = enum
    lines = ["-- Generated by scripts/generate-zellij-lua.py; do not edit.",
             f"-- Source: https://github.com/lanej/zellij/tree/{revision}/zellij-utils/src/client_server_contract",
             "-- stylua: ignore", "return {", "\tmessages = {"]
    for name, message in sorted(messages.items()):
        entry = ", map_entry = true" if message.options.map_entry else ""
        lines.append(f'\t\t[{lua(name)}] = {{ fields = {{')
        for field in message.field:
            kind = KINDS[field.type]
            if kind not in {"bool", "bytes", "enum", "float", "int32", "message", "string", "uint32", "uint64"}:
                raise SystemExit(f"Add codec support for protobuf field kind {kind}")
            attributes = {"name": field.name, "tag": field.number, "kind": kind}
            if field.type_name:
                attributes["ref"] = field.type_name.lstrip(".")
            if field.label == field.LABEL_REPEATED:
                attributes["repeated"] = True
                if kind not in ("message", "string", "bytes") and (
                    field.options.packed if field.options.HasField("packed") else True
                ):
                    attributes["packed"] = True
            if field.HasField("oneof_index"):
                attributes["oneof"] = message.oneof_decl[field.oneof_index].name
            lines.append("\t\t\t" + lua(attributes) + ",")
        lines.append("\t\t}" + entry + " },")
    lines.extend(["\t},", "\tenums = {"])
    for name, enum in sorted(enums.items()):
        lines.append(f'\t\t[{lua(name)}] = {lua({value.name: value.number for value in enum.value})},')
    lines.extend(["\t},", "}", ""])
    return {ROOT / "nvim/lua/zellij/schema.lua": "\n".join(lines),
            ROOT / "nvim/tests/zellij-protobuf.json": json.dumps(fixtures(pool, messages), ensure_ascii=False, indent=2) + "\n"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for destination, generated in generate().items():
        if args.check:
            if destination.read_text() != generated:
                raise SystemExit("Zellij Lua bindings are stale; run uv run scripts/generate-zellij-lua.py")
        else:
            destination.write_text(generated)


if __name__ == "__main__":
    main()
