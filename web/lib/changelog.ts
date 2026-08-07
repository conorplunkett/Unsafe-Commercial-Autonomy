// Minimal markdown parser scoped to CHANGELOG.md's own shape: "## [date] title"
// entries, "### " subheadings, "- " bullet lists (optionally nested by
// indentation, with wrapped continuation lines folded back into one item),
// and plain paragraphs. Not a general CommonMark parser — just enough to
// render the changelog without adding a markdown dependency.

export interface ListItem {
  text: string;
  children: ListItem[];
}

export type Block =
  | { kind: "h3"; text: string }
  | { kind: "p"; text: string }
  | { kind: "list"; items: ListItem[] };

export interface ChangelogEntry {
  date: string;
  title: string;
  body: Block[];
}

const LIST_MARKER = /^(\s*)(?:[-*]|\d+\.)\s+(.*)$/;

function parseListLines(lines: string[]): { indent: number; text: string }[] {
  const entries: { indent: number; text: string }[] = [];
  for (const line of lines) {
    const m = LIST_MARKER.exec(line);
    if (m) {
      entries.push({ indent: m[1].length, text: m[2].trim() });
    } else if (entries.length > 0 && line.trim() !== "") {
      entries[entries.length - 1].text += " " + line.trim();
    }
  }
  return entries;
}

function buildItemTree(
  entries: { indent: number; text: string }[],
  pos: { i: number },
  parentIndent: number,
): ListItem[] {
  const items: ListItem[] = [];
  while (pos.i < entries.length && entries[pos.i].indent === parentIndent) {
    const entry = entries[pos.i];
    pos.i++;
    let children: ListItem[] = [];
    if (pos.i < entries.length && entries[pos.i].indent > parentIndent) {
      children = buildItemTree(entries, pos, entries[pos.i].indent);
    }
    items.push({ text: entry.text, children });
  }
  return items;
}

function parseBody(text: string): Block[] {
  const lines = text.split("\n");
  const blocks: Block[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    if (line.trim() === "") {
      i++;
      continue;
    }
    if (line.startsWith("### ")) {
      blocks.push({ kind: "h3", text: line.slice(4).trim() });
      i++;
      continue;
    }
    if (LIST_MARKER.test(line)) {
      const listLines: string[] = [];
      while (
        i < lines.length &&
        (lines[i].trim() === "" ? false : true) &&
        !lines[i].startsWith("### ")
      ) {
        if (lines[i].trim() === "") break;
        listLines.push(lines[i]);
        i++;
      }
      const entries = parseListLines(listLines);
      const baseIndent = entries[0]?.indent ?? 0;
      const items = buildItemTree(entries, { i: 0 }, baseIndent);
      blocks.push({ kind: "list", items });
      continue;
    }
    // Paragraph: consecutive non-blank, non-heading, non-list lines.
    const paraLines: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !lines[i].startsWith("### ") &&
      !LIST_MARKER.test(lines[i])
    ) {
      paraLines.push(lines[i].trim());
      i++;
    }
    blocks.push({ kind: "p", text: paraLines.join(" ") });
  }

  return blocks;
}

const ENTRY_HEADER = /^\[(\d{4}-\d{2}-\d{2})\]\s*(.*)$/;

export function parseChangelog(md: string): ChangelogEntry[] {
  const withoutTitle = md.replace(/^#\s+.*\n/, "");
  const chunks = withoutTitle.split(/\n(?=## )/).filter((c) => c.trim() !== "");

  const entries: ChangelogEntry[] = [];
  for (const chunk of chunks) {
    const stripped = chunk.replace(/^## /, "");
    const newlineIdx = stripped.indexOf("\n");
    const headerLine =
      newlineIdx === -1 ? stripped : stripped.slice(0, newlineIdx);
    const rest = newlineIdx === -1 ? "" : stripped.slice(newlineIdx + 1);

    const m = ENTRY_HEADER.exec(headerLine.trim());
    if (!m) continue;
    entries.push({
      date: m[1],
      title: m[2].trim(),
      body: parseBody(rest),
    });
  }
  return entries;
}
