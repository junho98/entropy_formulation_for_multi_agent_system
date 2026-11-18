# CLAUDE.md — Slidev presentation authoring guide

This directory is a Slidev presentation project. Your job is to generate/edit
`slides.md` based on the source material in `docs/notes.md` and the assets in
`public/`.

A human runs the project via `run_presentation.sh`, so you only produce
`slides.md` and any needed components. Do NOT run `npm run dev` or start a
server.

---

## 1. Workflow

1. Read `docs/notes.md` first. The goal, audience, key messages, and slide
   mapping live there.
2. Check the assets (figures, videos) under `public/`.
3. Write `slides.md` according to the slide mapping in notes.
4. If the mapping is empty, do NOT place things arbitrarily — ask what
   information is missing first.

---

## 2. Path rules (the most common mistake)

- All assets live under `public/`. **Not `assets/`.**
- In markdown, reference images by **root-absolute path**. Do NOT put `public/`
  in the path.

  ```markdown
  <!-- correct: points to public/images/foo.png -->
  ![caption](/images/foo.png)

  <!-- wrong -->
  ![caption](public/images/foo.png)
  ![caption](./assets/images/foo.png)
  ```

- Following this rule keeps images intact in both `dev` and `export` (PDF).
  Relative paths break on export.

---

## 3. Slide authoring rules

- **One slide = one message.** Do not cram multiple claims into one slide.
- Separate slides with `---` (blank line before and after).
- Put global settings (theme, title) in the first slide's frontmatter. Keep
  the deck headmatter and slide 1's frontmatter as ONE block (e.g. put
  `layout: cover` in the same block as `theme:`/`title:`), and that block MUST
  start on line 1 of the file. A comment/blank line before it, or splitting it
  into two `---...---` blocks, makes Slidev render the global `title:` as an
  empty phantom slide before your real first slide.
- Set a per-slide layout via `layout:` in that slide's frontmatter.

Bundled layouts:

| Purpose | layout |
|---------|--------|
| Title slide (navy band) | `cover` |
| Table of contents | `outline` |
| Section divider (full navy) | `section` |
| Two columns (text + figure) | `two-cols-fig` |
| Three columns (dense / appendix) | `three-cols-fig` |
| Body (title via frontmatter) | `body` |

Content layouts (`body`, `two-cols-fig`) draw their title from the frontmatter
`slideTitle:` (and optional `sub:`) — do NOT use a markdown `# heading` for
these. Use markdown `#` only on `section`/`cover`.

Title style is chosen per slide with `titleStyle:`:
- `navy` (default) — navy header band
- `plain` — plain h1, no band

The `cover` layout's logo is set with `logo:` (image path under `public/`, e.g.
`/images/aail-logo.png`); if omitted it falls back to the `org:` text.

Helper classes available from the global stylesheet: `navy-title`, `box`,
`box-soft`, `cols2`, `cite`, `subtitle`, `accent`, `danger`, `success`,
`muted`, `fig-ph`, `todo`, `eq-sm`, `eq-xs`, `dense`, `appendix`.

- `fig-ph` — dashed-border figure placeholder for figures not yet generated,
  e.g. `<div class="fig-ph">[figure: KEY]</div>`. Replace with the real
  `![caption](/images/KEY.png)` once the asset exists.
- `todo` — small orange italic marker for body content not yet filled in.
- `eq-sm` / `eq-xs` — display math uses one uniform size everywhere (3-column
  appendix is slightly smaller); it is NOT auto-shrunk per slide. If a single
  equation overflows, wrap just that one: `<div class="eq-sm"> $$ ... $$ </div>`
  (one notch down) or `<div class="eq-xs"> $$ ... $$ </div>` (two notches).
- `dense` — set on a slide via frontmatter `class: dense` (NOT an inline div)
  when a whole slide overflows the 551px canvas vertically (theorem + lemmas +
  stacked equations, many figures, etc.). It tightens body text and list
  spacing only; it does NOT change equation size (math stays uniform).
- `appendix` — frontmatter `class: appendix` (often `class: dense appendix`)
  for proof-dump reference slides where everything must fit on one slide. This
  is the ONE helper that shrinks math below the global baseline — intentional,
  because uniform equation size cannot coexist with cramming a full proof in.

`cover` example:

```markdown
---
layout: cover
coverTitle: My Talk
author: Junho Kim
date: 30 Apr 2026
org: AAiL
---

<div class="subtitle">Subtitle</div>
```

`body` example (title becomes a navy band by default; content goes below):

```markdown
---
layout: body
slideTitle: Method
sub: overview
# titleStyle: plain   # optional: plain h1 instead of navy band
---

- point 1
- point 2

<div class="box">key result</div>
```

`outline` example (highlights item N):

```markdown
---
layout: outline
active: 2
items:
  - Background
  - Method
  - Results
---
```

`two-cols-fig` example:

```markdown
---
layout: two-cols-fig
slideTitle: Method
sub: overview
---

- point 1
- point 2

::right::

![result](/images/result.png)
```

`three-cols-fig` example (slots: default / `::middle::` / `::right::`):

```markdown
---
layout: three-cols-fig
slideTitle: Appendix A
---

left column

::middle::

middle column

::right::

right column
```

---

## 4. Diagrams

- For simple flow/structure diagrams, use Slidev's built-in Mermaid code
  blocks. Do NOT pre-render with external `mmdc`.

  ````markdown
  ```mermaid
  graph LR
    A[V_gt] --> B[V_smooth] --> C[V_koopman]
  ```
  ````

- For heavy math or paper figures that must be reproduced exactly, insert the
  `public/images/*.png` specified in notes. Do NOT try to recreate them in
  Mermaid.
- Math can be written in LaTeX directly: inline `$...$`, block `$$...$$`.

---

## 5. Video

- Video does not work via markdown. Use an HTML `<video>` tag.

  ```markdown
  <video controls class="h-80 mx-auto">
    <source src="/videos/demo.mp4" type="video/mp4" />
  </video>
  ```

- **Note: on export (PDF), video becomes a still frame / blank.** If notes mark
  the talk as a PDF deliverable, ask whether a key-frame PNG fallback should be
  added to video slides.

---

## 6. Do NOT

- Reference `assets/` paths (→ use `public/` + root-absolute path)
- Use relative image paths (`./`, `../`)
- Pre-render with external mmdc (→ use built-in mermaid)
- Place figures arbitrarily when notes have no mapping (→ ask)
- Run the server (→ a human does that)
- Put multiple messages on one slide
