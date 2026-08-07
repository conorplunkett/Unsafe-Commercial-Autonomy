# Design system

Everything visual on this site resolves to a token in `app/globals.css` or a
component in `components/ui/`. Two rules keep it that way:

1. **No raw values in components.** No hex colours, no `text-[0.85rem]`, no
   hand-built panel shells. If you need something the tokens don't cover, add a
   token here first.
2. **A new step needs a reason.** The scale below replaced 23 ad-hoc font sizes.
   Adding a 15th step because a heading looks 1px off puts us back there.

## Colour

Ten tokens, defined in the `@theme` block. Tailwind generates every
`bg-`/`text-`/`border-` utility from them, so changing a token changes the site.

| Token | Value | Role |
| --- | --- | --- |
| `paper` | `#fbf7ec` | page background |
| `paper-2` | `#f2ead6` | panel fill (always used at low opacity) |
| `border` | `#e5dcc7` | hairlines, panel edges |
| `ink` | `#1b1713` | body text |
| `muted` | `#7c7163` | secondary text, labels |
| `block` | `#15110d` | near-black blocks |
| `accent` | `#1a6b59` | links, active nav, the safe/lookalike side |
| `accent-2` | `#2f8f74` | charts, second series |
| `danger` | `#b4472b` | unsafe rates, traps, errors |
| `warn` | `#bf8a2d` | refused-when-safe, cautions |

One exception exists on purpose: `app/opengraph-image.tsx` hardcodes five hexes
because Satori renders it at build time and can't read CSS variables. **Change a
colour there too, or the social card drifts from the site.**

## Type scale

Tailwind's default sizes are cleared (`--text-*: initial`), so `text-sm` and
`text-3xl` no longer resolve to anything. Every size comes from a step below,
and each step is named for its role rather than its pixels — `text-h2`, not
`text-3xl`, so a later retune doesn't leave the class names lying about what
they do.

| Step | Size | Line height | Used for |
| --- | --- | --- | --- |
| `text-micro` | 0.65rem / 10.4px | 1.45 | mono in dense table cells and badges |
| `text-label` | 0.7rem / 11.2px | 1.45 | the `.label` eyebrow, chart captions |
| `text-caption` | 0.75rem / 12px | 1.5 | mono metadata, fine print |
| `text-small` | 0.875rem / 14px | 1.55 | secondary UI text, table body |
| `text-compact` | 0.95rem / 15.2px | 1.55 | dense serif tables |
| `text-ui` | 1.05rem / 16.8px | 1.5 | nav, links, buttons, list items |
| `text-prose` | 1.125rem / 18px | 1.7 | long-form paragraphs |
| `text-h4` | 1.25rem / 20px | 1.35 | card titles |
| `text-h3` | 1.5rem / 24px | 1.25 | sub-headings |
| `text-stat` | 1.7rem / 27.2px | 1.05 | the big number in a stat tile |
| `text-quote` | 20 → 24px, fluid | 1.25 | pull quotes, the hero lede |
| `text-h2` | 30 → 36px, fluid | 1.15 | section headings |
| `text-h1` | 36 → 48px, fluid | 1.1 | sub-page titles |
| `text-display` | 60 → 80px, fluid | 0.98 | the hero wordmark |

Steps sit close together through the UI range, where a pixel is a real decision,
and open up at the display end.

**The four largest steps are fluid.** They interpolate between a 640px and a
1280px viewport via `clamp()`, so headings take no `sm:` variant — `text-h2`
alone replaces `text-3xl sm:text-4xl`. Don't add a breakpoint to a heading;
retune the clamp.

Line heights ship with the step. A `leading-*` utility on the same element
overrides it, which is how the tighter pull quotes and the looser hero lede
still work — but reach for that only when the default is genuinely wrong.

### Retuning

Editing a step in `globals.css` moves every use of it. Making body copy larger
is `--text-prose`, one line. That is the whole point of the layer; resist fixing
one page with a local override.

## The Card

`components/ui/Card.tsx` is the panel shell — rounded box, border, optional
tint. It replaced fifteen hand-written variants whose fill opacity (`/40`,
`/50`, `/60`) and padding (`p-4`, `p-5`, `px-5 py-4`) had drifted apart.

```tsx
<Card>…</Card>                              // tinted panel, p-5
<Card tone="raised" pad="sm">…</Card>       // on top of a tinted parent
<Card as="ol" tone="bare" pad="none">…</Card>  // wrapping a table or striped list
```

| `tone` | Fill | Use |
| --- | --- | --- |
| `tint` *(default)* | `paper-2/40` | the panel that carries most content |
| `raised` | `paper` | sits on top of a tinted parent, or reads as front-most |
| `bare` | none | outline only, for panels wrapping their own rows |
| `accent` | `accent/5` | the safe / lookalike side of a pair |
| `danger` | `danger/4` | the trap side of a pair |
| `alert` | `danger/10` | an error the user has to act on |

`pad` is `md` (p-5, default), `sm` (p-4), or `none` when the child owns its
padding. `as` swaps the element (`div`, `details`, `article`, `aside`, `ol`,
`p`); everything else passes through, so `key`, `id`, and extra `className` work
as usual.

Chips, buttons, inputs, tooltips, and code blocks are *not* Cards — they use
`rounded-md`/`rounded-lg` and are still inline. If they start drifting, they get
their own component here rather than a `Card` variant.

## Deliberately absent

- **No dark mode.** The palette is a warm printed-paper look and the site is
  single-theme by choice. Don't add `dark:` variants.
- **No second scale.** The static pages in `public/` (`survey.html`,
  `admin.html`) carry their own unrelated palette and are out of scope. Nothing
  here applies to them, and nothing there should be copied back.

## Layout

Content sits in a `max-w-5xl` column. Sections are separated by
`SectionDivider` (or `ToggleSection`, which collapses), both of which own the
`mt-20 … border-t … pt-8` rhythm — change section spacing there, not per page.
