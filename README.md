# chennoshen239.github.io

Source for my academic homepage, https://chennoshen239.github.io. Plain HTML and one stylesheet (`assets/site.css`), served by GitHub Pages from `main`. There is no build step.

- Header and footer are repeated in `index.html`, `research.html`, `notes.html` and `teaching.html`; change all four.
- Fonts are self-hosted in `assets/fonts/` because Google Fonts is blocked in mainland China. The Noto Serif SC files only contain 高 and 琛.
- The note sites (`*-notes/`) are separate Quarto builds with their own styles. The old Quarto source of the homepage is on the `legacy-quarto` branch; don't publish it over `main`.
- Keep `.nojekyll`.
- When adding a paper or notes, add an item to `feed.xml` and check it with `xmllint --noout feed.xml`.

Preview locally:

```sh
python3 -m http.server 8000
```

then open http://localhost:8000.
