"""Independent wire helpers for the small Action/Log socket fixtures."""
import socket
import struct
import threading
from contextlib import contextmanager


def varint(value):
    result = bytearray()
    while value > 127:
        result.append((value & 127) | 128)
        value >>= 7
    return bytes(result + bytes([value]))


def message(tag, value):
    return varint(tag * 8 + 2) + varint(len(value)) + value


def fields(data):
    position = 0

    def integer():
        nonlocal position
        result, shift = 0, 0
        while True:
            byte = data[position]
            position += 1
            result |= (byte & 127) << shift
            if byte < 128:
                return result
            shift += 7

    result = {}
    while position < len(data):
        key = integer()
        if key % 8 == 0:
            result[key >> 3] = integer()
        else:
            assert key % 8 == 2, key
            length = integer()
            result[key >> 3] = data[position:position + length]
            position += length
    return result


@contextmanager
def action_server(listener, reply):
    """Pass decoded ActionMsg fields to reply; None simulates a lost acknowledgement."""
    stopped, errors = threading.Event(), []
    listener.listen()
    listener.settimeout(0.05)

    def serve():
        try:
            while not stopped.is_set():
                try:
                    connection, _ = listener.accept()
                except socket.timeout:
                    continue
                with connection:
                    connection.settimeout(1)

                    def receive(length):
                        data = b""
                        while len(data) < length:
                            part = connection.recv(length - len(data))
                            assert part, "Incomplete request"
                            data += part
                        return data

                    length = struct.unpack("<I", receive(4))[0]
                    assert length <= 4 * 1024 * 1024
                    response = reply(fields(fields(receive(length))[9]))
                    if response is not None:
                        connection.sendall(struct.pack("<I", len(response)) + response)
        except Exception as error:
            errors.append(error)

    worker = threading.Thread(target=serve)
    worker.start()
    try:
        yield
    finally:
        stopped.set()
        worker.join(timeout=2)
        assert not worker.is_alive(), "Fixture server failed to stop"
        assert not errors, errors
