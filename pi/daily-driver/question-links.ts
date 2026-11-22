import { hyperlink, stripTerminalSequences } from "@earendil-works/pi-tui";

export function questionText(value: string): string {
  return stripTerminalSequences(value).replace(/[^\P{Cc}\n\t]/gu, " ");
}

export function questionLink(label: string, url: string): string {
  const text = questionText(label).replace(/\s+/gu, " ");
  const target = URL.parse(url);
  return target?.protocol === "https:" || target?.protocol === "http:"
    ? hyperlink(text, target.href)
    : text;
}

export function questionLinks(value: string): string {
  return questionText(value).replace(
    /\[([^\]\n]+)\]\((https?:\/\/[^\s<>()]+)\)|(https?:\/\/[^\s<>()[\]]+)/giu,
    (
      match: string,
      label: string | undefined,
      markdown: string | undefined,
      bare: string | undefined,
    ) => {
      if (label !== undefined && markdown !== undefined)
        return questionLink(label, markdown);
      if (bare === undefined) return match;
      const url = bare.replace(/[.,;!?]+$/u, "");
      return questionLink(url, url) + bare.slice(url.length);
    },
  );
}
