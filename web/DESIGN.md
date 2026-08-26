# Design system — Forest Precision

Everything visual on this site resolves to a token in `app/globals.css` or a
component in `components/ui/`. Two rules keep it that way:

1. **No raw values in components.** No hex colours, no `text-[0.85rem]`, no
   hand-built panel shells. If you need something the tokens don't cover, add
   a token here first.
2. **A new step needs a reason.** The scale below replaced 23 ad-hoc font
   sizes once already. Adding an eleventh step because a heading looks a pixel
   off puts us back there.

## Brand

Clarity, precision, trust — the register of a modern financial-infrastructure
product. Structural rather than decorative: hierarchy comes from type weight
and 1px rules, not shadows or ornament. The ground is **pure white**, on
purpose; no cream, ivory, or tinted greys.

## Colour

Eleven tokens in the `@theme` block. Tailwind generates every `bg-`/`text-`/
`border-` utility from them, so changing a token changes the site.

| Token      | Value     | Role                                         |
| ---------- | --------- | -------------------------------------------- |
| `paper`    | `#ffffff` | the page                                     |
| `paper-2`  | `#f1f5f9` | panel and chip fill                          |
| `border`   | `#e2e8f0` | hairlines, panel edges                       |
| `ink`      | `#0b1c30` | body text                                    |
| `muted`    | `#556274` | secondary text, labels                       |
| `block`    | `#213145` | inverted surface (taxonomy tiles)            |
| `accent`   | `#1b5e55` | brand: links, primary actions, correct-state |
| `accent-2` | `#93d3c7` | second chart series                          |
| `danger`   | `#ba1a1a` | unsafe payment                               |
| `warn`     | `#7c4634` | refused when safe                            |
| `flag`     | `#c2410c` | attention: a scenario still needs review     |

Every text pair clears WCAG AA on both `paper` and `paper-2`; `ink`, `accent`
and `warn` clear AAA. Re-check with the contrast script in the PR if you
change one.

Two colour-semantic maps exist outside the tokens and must stay in step:
`components/results/Donut.tsx` (confusion-matrix segments) and
`components/survey/QuestionCard.tsx` (`PROCEED_CLASSES`).

One exception on purpose: `app/opengraph-image.tsx` hardcodes five hexes
because Satori renders it at build time and can't read CSS variables.
**Change a colour there too, or the social card drifts from the site.** Same
for `app/icon.svg` and `app/favicon.ico` (regenerate the `.ico` with `sharp`
from the SVG — see the PR that introduced it).

## Typography

Three faces, each with a job:

| Face               | Carries                                                        |
| ------------------ | -------------------------------------------------------------- |
| **Inter**          | everything by default — headings, nav, labels, buttons, tables |
| **Newsreader**     | long-form prose only                                           |
| **JetBrains Mono** | data: scenario IDs, rates, matrices, code                      |

### The one rule that matters

`body` is **Inter**. Long-form copy therefore has to say `font-serif`
explicitly — it will not inherit it.

The marker is `text-prose` + `leading-relaxed`; every element with both must
also carry `font-serif`. There's a check for exactly this in the PR that
introduced the identity, and it's worth re-running after any copy change.

Note that `text-prose` alone is just the 18px step — it's also used for
18px _titles_, which correctly stay Inter. Size and family are separate
decisions here.

### Scale

Tailwind's default sizes are cleared (`--text-*: initial`), so `text-sm` and
`text-3xl` no longer resolve. Every size comes from a step below, named for
its role rather than its pixels. Weight and tracking ship with the step, so a
heading never has to remember them.

| Step           | Size / leading | Weight | Role                           |
| -------------- | -------------- | ------ | ------------------------------ |
| `text-caption` | 12 / 16        | 600    | eyebrows, badges, table cells  |
| `text-small`   | 14 / 20        | 400    | secondary UI, table body, nav  |
| `text-ui`      | 16 / 24        | 400    | buttons, list items            |
| `text-prose`   | 18 / 29.7      | 400    | long-form paragraphs _(serif)_ |
| `text-h4`      | 20 / 28        | 600    | card titles, the nav wordmark  |
| `text-h3`      | 20 → 24, fluid | 600    | sub-headings, pull quotes      |
| `text-stat`    | 32 / 40        | 600    | the big number in a stat tile  |
| `text-h2`      | 28 → 32, fluid | 600    | section headings               |
| `text-h1`      | 36 → 48, fluid | 700    | page titles                    |
| `text-display` | 48 → 72, fluid | 700    | the hero wordmark              |

The four fluid steps interpolate between 640px and 1280px viewports, so a
heading takes **no `sm:` variant**. Don't add a breakpoint to a heading;
retune the clamp.

`text-h4` is deliberately fixed rather than fluid — the nav wordmark uses it,
and the nav breaks onto two lines if it grows.

## The Card

`components/ui/Card.tsx` is the panel shell. It replaced fifteen hand-written
variants whose fill opacity and padding had drifted apart.

```tsx
<Card>…</Card>                                 // tinted panel, p-5
<Card tone="raised" pad="sm">…</Card>          // on top of a tinted parent
<Card as="ol" tone="bare" pad="none">…</Card>  // wrapping a table or list
```

Tones: `tint` (default), `raised`, `bare`, `accent`, `danger`, `alert`.
`pad` is `md` / `sm` / `none`. `as` swaps the element; everything else passes
through, so `key`, `id` and extra `className` work as usual.

Fills are **solid**, not opacity blends — over pure white a 40% tint is
invisible.

Chips, buttons, inputs and tooltips are _not_ Cards.

## Shape and elevation

8px is the base radius. In stock Tailwind v4 that is `rounded-lg`; the ladder
we use is `rounded` (4px, small elements) → `rounded-lg` (8px, buttons,
inputs, chips) → `rounded-2xl` (16px, cards and large containers) →
`rounded-full` (pills).

Hierarchy comes from 1px borders, not shadows. Only two things in the site
carry a shadow — the hero PDF frame and the term tooltip — and both use the
diffuse, low-opacity `0 4px 12px rgba(0,0,0,0.05)`.

## Interactive targets

Anything tappable is at least **44×44 CSS px** (Apple HIG, WCAG 2.5.5 AAA).
This supersedes Forest Precision's 40px standard button height — these are
thumb targets on a phone.

`.tap` for elements that centre their own content (a `<button>` does),
`.tap-link` for anchors that don't.

> Both live inside `@layer components`, and must stay there. `.tap-link` sets
> `display`, and a utility like `hidden` or `sm:inline-flex` has to be able to
> win over it. Left in the bare stylesheet it outranks them and `hidden`
> silently stops working.

Exempt, and adding `.tap` to either is wrong: **inline links inside a
paragraph** (WCAG exempts them, and 44px would wreck the line rhythm), and
**a small control wholly inside a large label** — the runner's 16px radios sit
in full-width rows, and the label is the target.

## Layout

Content sits in a `max-w-5xl` (1024px) column with a 16px → 32px margin.
Spacing follows an 8px rhythm — prefer the even Tailwind steps (`2`, `4`,
`6`, `8`, `12`, `20`); 4px and 12px are allowed as half-steps.

Section rhythm lives in `SectionDivider` and `ToggleSection` — change it
there, not per page.

Each page's `<main>` carries `overflow-x-clip` so an absolutely-positioned
decoration can't widen the page. `clip` rather than `hidden`, so it doesn't
create a scroll container and the sticky nav keeps working.

## Deliberately absent

- **No dark mode.** Single-theme by choice. Don't add `dark:` variants.
- **No second scale.** The static pages in `public/` (`survey.html`,
  `admin.html`) carry their own unrelated palette and are out of scope.

## Deviations from the Forest Precision spec

Recorded so they read as decisions, not drift.

| Spec says                       | We do                          | Why                                                                 |
| ------------------------------- | ------------------------------ | ------------------------------------------------------------------- |
| Inter at every level            | Newsreader for long-form prose | The site's main job is reading a paper                              |
| No monospace role               | JetBrains Mono for data        | Scenario IDs, rates and matrices need it                            |
| `background: #f8f9ff` (tokens)  | `#ffffff`                      | The spec's own prose says "strictly pure white, avoid tinted greys" |
| `primary #00463e` (tokens)      | `#1b5e55`                      | The spec's prose names this as the brand green                      |
| Green-tinted `outline` (tokens) | Slate neutrals                 | The spec's prose specifies slate; consistent with pure white        |
| Secondary text `#64748B`        | `#556274`                      | `#64748B` is only 4.34:1 on `paper-2` — below AA                    |
| Strict 8px multiples            | 8px rhythm, 4/12 as half-steps | The spec's own scale ships `xs: 4px` and `sm: 12px`                 |
| `headline-lg-mobile` role       | dropped                        | Byte-identical to `headline-md`; our fluid clamp already handles it |
| No warn colour                  | `tertiary` rust as `warn`      | The taxonomy needs three outcome states, not two                    |
| Buttons 40px                    | 44px minimum                   | Accessibility floor, see above                                      |
| 1440px / 12-column grid         | 1024px reading column          | 1440px runs a paragraph far past a readable measure                 |
| `body-lg` at 18/28              | 18/29.7                        | Newsreader needs more leading than Inter at the same size           |
