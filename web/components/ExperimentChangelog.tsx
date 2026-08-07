import fs from "fs";
import path from "path";
import type { ReactNode } from "react";
import { ToggleSection } from "./ToggleSection";
import { parseChangelog, type Block, type ListItem } from "@/lib/changelog";
import { renderInline } from "@/lib/renderInline";

// Reads the repo-root CHANGELOG.md at build time and renders it as-is — this
// section carries no separate copy of its own, so the changelog can't drift
// from what actually shipped. See CHANGELOG.md for the canonical source.
function readChangelog(): string {
  try {
    return fs.readFileSync(
      path.join(process.cwd(), "..", "CHANGELOG.md"),
      "utf-8",
    );
  } catch {
    return "";
  }
}

function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  const date = new Date(Date.UTC(y, m - 1, d));
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

function renderListItems(items: ListItem[]): ReactNode {
  return (
    <ul className="list-disc space-y-1.5 break-words pl-5 marker:text-accent">
      {items.map((item, idx) => (
        <li key={idx}>
          {renderInline(item.text)}
          {item.children.length > 0 && (
            <ul className="mt-1.5 list-disc space-y-1.5 pl-5 marker:text-accent/70">
              {item.children.map((child, cidx) => (
                <li key={cidx}>{renderInline(child.text)}</li>
              ))}
            </ul>
          )}
        </li>
      ))}
    </ul>
  );
}

function renderBlock(block: Block, idx: number) {
  switch (block.kind) {
    case "h3":
      return (
        <h4 key={idx} className="mt-4 font-serif text-base font-semibold">
          {block.text}
        </h4>
      );
    case "p":
      return (
        <p key={idx} className="mt-2 break-words leading-relaxed text-ink/85">
          {renderInline(block.text)}
        </p>
      );
    case "list":
      return (
        <div key={idx} className="mt-2 text-ink/85">
          {renderListItems(block.items)}
        </div>
      );
  }
}

export function ExperimentChangelog() {
  const raw = readChangelog();
  if (!raw.trim()) return null;
  const entries = parseChangelog(raw);
  if (entries.length === 0) return null;

  return (
    <ToggleSection id="changelog" title="Changelog">
      <div className="mt-6 space-y-2">
        {entries.map((entry, i) => (
          <details
            key={i}
            className="group/entry rounded-lg border border-border px-4 py-3"
          >
            <summary className="flex cursor-pointer list-none items-baseline gap-3 marker:content-none [&::-webkit-details-marker]:hidden">
              <span
                aria-hidden
                className="inline-block text-sm text-accent transition-transform duration-150 group-open/entry:rotate-90"
              >
                ▸
              </span>
              <span className="font-mono text-xs text-muted">
                {formatDate(entry.date)}
              </span>
              <span className="font-serif text-[1.05rem] leading-snug">
                {entry.title}
              </span>
            </summary>
            <div className="mt-3 border-t border-border pl-7 pt-3 text-sm">
              {entry.body.map((block, bidx) => renderBlock(block, bidx))}
            </div>
          </details>
        ))}
      </div>
    </ToggleSection>
  );
}
