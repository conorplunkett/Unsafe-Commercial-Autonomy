<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# Design system

`DESIGN.md` in this directory is the source of truth for colour, type, and the
`Card` shell. **Read it before writing any markup or CSS.**

The short version:

- Colour and font size come from tokens in `app/globals.css`. Never write a hex
  value or an arbitrary size like `text-[0.85rem]` in a component.
- Tailwind's default type scale is cleared, so `text-sm` / `text-3xl` resolve to
  nothing. Use the named steps (`text-small`, `text-h2`, …). A stray legacy class
  fails silently — it won't break the build, the text just inherits its size.
- Headings are fluid and take no `sm:` variant.
- Panels use `<Card>` from `components/ui/Card.tsx`, not a hand-rolled
  `rounded-xl border …`.
- The site is single-theme. No dark mode, no `dark:` variants.
