# Chen Gao — personal website

The **`main` branch is the live, hand-edited static site** served at <https://chennoshen239.github.io>.
GitHub Pages serves from `main` / root (Settings → Pages; legacy branch-deploy, no Actions, no build step).
Edit the HTML/CSS on `main` and push. Plain HTML + two shared CSS files + self-hosted fonts. No JS framework, no Quarto.

> ⚠️ **One live branch only: `main`.** The old Quarto source is archived on the **`legacy-quarto`** branch,
> kept for reference. Never `quarto publish` it or merge it into `main`; that would overwrite this
> hand-authored static site. (History: the site used to live on a separate `gh-pages` branch with `main`
> holding Quarto; those were consolidated into a single `main`.)

---

## Where to change what

| You want to change… | Edit this |
|---|---|
| Page text, papers, news, links, nav labels | the four page files: `index.html`, `research.html`, `notes.html`, `teaching.html` |
| Colors, type sizes, fonts in use, spacing, buttons, animations, responsive | `assets/site.css` — design tokens are the CSS variables in `:root{…}` at the very top |
| Which font files load (`@font-face`) | `assets/fonts.css` + the `.woff2` files in `assets/fonts/` |
| Portrait photo | `assets/img/portrait.jpg` |
| Social / OpenGraph share card (1200×630) | `assets/img/og.png` (referenced in each page `<head>`) |
| CV and paper PDFs | `files/` — e.g. `files/cv.pdf`, `files/bounded_default.pdf`, `files/iesn-notes.pdf`, `files/dmp-notes.pdf` |
| SEO / metadata | the `<head>` of each page (title, description, canonical, OG/Twitter, JSON-LD on `index.html`) + `sitemap.xml` + `robots.txt` |
| The DMP lecture note | Now a **PDF**: `files/dmp-notes.pdf`, compiled from the owner's LyX master at `Website/notes/DMP.lyx`. To update, recompile that LyX → PDF and overwrite the file. `notes/dmp.html` is just a redirect to the PDF (the Quarto/HTML version is retired). |

The header / nav / footer markup is **duplicated in all four page files** (there are no includes).
If you change the nav, the wordmark, or the footer, update all four by hand. The active nav link is
marked with `aria-current="page"`.

---

## Design system (current)

- **Fonts** (defined in `assets/fonts.css`, self-hosted under `assets/fonts/`):
  - **Space Grotesk** — headings, wordmark, nav, labels, dates, buttons, footer (all the sans UI). Weights 400/500/700.
  - **Spectral** — serif body prose (regular + italic).
  - **Noto Serif SC** — *only* the Chinese name 高琛 (see the subset warning below).
- **CSS tokens** (`:root` in `site.css`): `--red:#94070a` (the CV red — the only accent color), `--red-2:#7a0608`,
  `--ink:#16181d`, `--text:#2a2f38`, `--muted:#4f5763`, `--body` (Spectral), `--sans` (Space Grotesk),
  `--maxw:1080px`, `--pad:40px`.
- **Buttons** are underline-links, not boxes: base `.btn` is ink text with a faint resting underline that
  turns red on hover; `.btn-primary` (Email) is red. They are class-driven — restyle in `site.css`, don't touch markup.
- Single responsive breakpoint at `max-width:760px`. All animations are gated behind `prefers-reduced-motion`.

---

## House rules & gotchas

- **No em-dashes (—) in prose.** Owner preference. En-dash numeric ranges (e.g. `2022–2026`) are fine.
- **Fonts must work from mainland China.** Google Fonts (`fonts.gstatic.com`) is **blocked** there, which is why
  fonts are self-hosted. To add/replace a font, fetch the `.woff2` from **Fontsource via jsDelivr** (reachable in China):
  `https://cdn.jsdelivr.net/fontsource/fonts/<family>@latest/latin-<weight>-normal.woff2`
  — drop it in `assets/fonts/` and add an `@font-face` rule in `fonts.css`.
- **Chinese text is subset to just 高 and 琛.** The Noto Serif SC `@font-face` blocks use
  `unicode-range:U+9AD8` (高) and `U+741B` (琛). Any *other* Chinese character will not render. To add more Chinese
  you must regenerate the Noto subset with the new glyphs **and** widen the `unicode-range`.
- **`.nojekyll` must stay** at the repo root (it stops GitHub Pages from running Jekyll over the files).
- **SSH to github.com is blocked on the owner's network.** Push over **HTTPS**. The owner's clone has an HTTPS remote
  named `deploy` → `https://github.com/ChennoShen239/chennoshen239.github.io.git`. `github.com:443` is sometimes flaky;
  just retry the push a few times.

---

## Deploy

```sh
# on the main branch of a clone of this repo
#   …edit the .html / assets/*.css …
git add -A
git commit -m "describe the change"
git push deploy main              # HTTPS remote; retry if it times out
```

GitHub Pages rebuilds in ~30–60s. The CDN can lag **per file** (one file updates before another), so verify the
live result with cache-busted requests, e.g.:

```sh
curl -s "https://chennoshen239.github.io/assets/site.css?cb=$RANDOM" | grep muted
```

## Preview locally

Open a page file in a browser, or screenshot it headless:

```sh
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new \
  --screenshot=out.png --window-size=1280,1700 --force-device-scale-factor=2 \
  "file:///ABS/PATH/index.html"
```

> Caveat: this headless build forces a **~500px minimum layout width**. So "mobile" screenshots are not truly
> 390px, and the right edge of desktop shots can look cropped. Don't diagnose overflow from the crop — measure it:
> compare `document.documentElement.scrollWidth` against `window.innerWidth`.

---

## Notes for future agents

- The richest running history of *why* things are the way they are lives in the owner's Claude memory
  (`personal-website-quarto.md`), not here.
- Content currently on the site: bilingual hero + bio (`index.html`); a working paper "Default with
  Policy-Randomness Overestimation" + a WIP inflation-forecasting paper (`research.html`); lecture/course
  notes + code links (`notes.html`); two TA roles (`teaching.html`).
- Keep it scholarly. This is an academic homepage for an economist; favor restraint over flourish.
