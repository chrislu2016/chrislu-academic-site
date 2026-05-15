# Chris Lu Academic Site

A lightweight, data-driven personal academic website for Lu Hongcheng (Chris Lu).

The site is generated with the Python standard library. There is no theme dependency and no package install step.

## Structure

- `data/site.json` is the main source of truth for profile, education, publications, conferences, projects, CV sections, and media.
- `src/assets/styles.css` controls the visual design.
- `scripts/build.py` generates the static website.
- `docs/` is the generated GitHub Pages output.

## Update Workflow

1. Edit `data/site.json`.
2. Add or replace assets in `src/assets/`.
3. Run:

```bash
python3 scripts/build.py
```

4. Preview `docs/index.html` in a browser.
5. Commit both the source files and the generated `docs/` files.

## GitHub Pages

For a standalone repository, set GitHub Pages to deploy from the `docs/` folder on the default branch.

## Media Notes

Video pages use:

```html
<video controls preload="metadata" playsinline>
```

This prevents the page from aggressively preloading video files and avoids the previous iframe behavior that could trigger downloads.
