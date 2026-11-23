import { hyperlink, stripTerminalSequences } from "@earendil-works/pi-tui";

export function selectorText(value: string): string {
  return stripTerminalSequences(value).replace(/[^\P{Cc}\n\t]/gu, " ");
}

export function selectorLink(label: string, url: string): string {
  const text = selectorText(label).replace(/\s+/gu, " ");
  const target = URL.parse(url);
  return target?.protocol === "https:" || target?.protocol === "http:"
    ? hyperlink(text, target.href)
    : text;
}

export function selectorLinks(value: string): string {
  return selectorText(value).replace(
    /\[([^\]\n]+)\]\((https?:\/\/[^\s<>()]+)\)|(https?:\/\/[^\s<>()[\]]+)/giu,
    (
      match: string,
      label: string | undefined,
      markdown: string | undefined,
      bare: string | undefined,
    ) => {
      if (label !== undefined && markdown !== undefined)
        return selectorLink(label, markdown);
      if (bare === undefined) return match;
      const url = bare.replace(/[.,;!?]+$/u, "");
      return selectorLink(url, url) + bare.slice(url.length);
    },
  );
}
