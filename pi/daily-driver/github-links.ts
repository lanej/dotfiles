import { hyperlink } from "@earendil-works/pi-tui";

export function githubLink(
  destination: string,
  compact = false,
): string | undefined {
  if (/[\p{Cc}\s\\]/u.test(destination)) return undefined;
  const url = URL.parse(destination);
  if (
    url === null ||
    url.origin !== "https://github.com" ||
    url.username !== "" ||
    url.password !== ""
  )
    return undefined;
  const [, owner, repo, route, subject, ...path] = url.pathname.split("/");
  if (
    owner === undefined ||
    repo === undefined ||
    !/^[\w.-]+$/u.test(owner) ||
    !/^[\w.-]+$/u.test(repo)
  )
    return undefined;
  const name = `${owner}/${repo}`;
  if (
    (route === "pull" || route === "issues") &&
    subject !== undefined &&
    /^[1-9]\d*$/u.test(subject)
  )
    return hyperlink(
      `${route === "pull" ? "" : "!"} ${compact ? "" : name}#${subject}`,
      url.href,
    );
  if (
    route === "commit" &&
    subject !== undefined &&
    /^[a-f0-9]{7,64}$/u.test(subject)
  )
    return hyperlink(`● ${name}@${subject.slice(0, 12)}`, url.href);
  if (route === "blob" && subject !== undefined && path.length > 0) {
    const file = path.at(-1) ?? "";
    const lines = /^#L(\d+)(?:-L(\d+))?$/u.exec(url.hash);
    const reference =
      lines === null
        ? ""
        : `:${lines[1] ?? ""}${lines[2] === undefined ? "" : `–${lines[2]}`}`;
    return hyperlink(`‹› ${file}${reference}`, url.href);
  }
  if (route === undefined || route === "")
    return hyperlink(` ${name}`, url.href);
  return undefined;
}

export function renderReferences(
  value: string,
  accent: (text: string) => string,
): string {
  return value.replace(
    /\[[^\]\n]+\]\((https:\/\/github\.com\/[^\s)]+)\)|(https:\/\/[^\s<>()]+)|(?<![\w/])(?:[\w.@+-]+\/)*[\w@+-]+\.[\w+-]+:\d+(?::\d+)?/gu,
    (match: string, markdown: string | undefined, bare: string | undefined) => {
      const target = markdown ?? bare;
      if (target === undefined) return accent(match);
      const trimmed =
        bare === undefined ? target : target.replace(/[.,;!?]+$/u, "");
      const link = githubLink(trimmed);
      return link === undefined
        ? match
        : accent(link) + target.slice(trimmed.length);
    },
  );
}
