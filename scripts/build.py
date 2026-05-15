#!/usr/bin/env python3
"""Build the bilingual static academic site from data/site.json."""

from __future__ import annotations

import json
import shutil
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "site.json"
DOCS = ROOT / "docs"
SRC_ASSETS = ROOT / "src" / "assets"
ASSETS = DOCS / "assets"
LANGS = ("en", "zh")


def h(value: object) -> str:
    return escape(str(value), quote=True)


def read_data() -> dict:
    with DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def rel_to_root(depth: int) -> str:
    return "../" * depth


def local_url(url: str, depth: int) -> str:
    if not url or url.startswith(("http://", "https://", "mailto:", "/")):
        return url
    return f"{rel_to_root(depth)}{url}"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def link(url: str, label: str, classes: str = "") -> str:
    if not url:
        return ""
    class_attr = f' class="{classes}"' if classes else ""
    return f'<a href="{h(url)}"{class_attr}>{h(label)}</a>'


def t(data: dict, lang: str, key: str) -> str:
    return data["ui"][lang][key]


def item_text(item: dict, field: str, lang: str) -> str:
    if lang == "zh" and item.get(f"{field}_zh"):
        return item[f"{field}_zh"]
    return item.get(field, "")


def brand_name(profile: dict, lang: str) -> tuple[str, str]:
    if lang == "zh":
        return profile["name_cn"], profile["preferred"]
    return profile["preferred"], profile["name"]


def hero_name(profile: dict, lang: str) -> tuple[str, str]:
    if lang == "zh":
        return profile["name_cn"], f'/ {profile["preferred"]}'
    return profile["preferred"], profile["name"]


def profile_card_name(profile: dict, lang: str) -> str:
    if lang == "zh":
        return f'{profile["name_cn"]} / {profile["preferred"]}'
    return f'{profile["name_cn"]} / {profile["name"]}'


def localized_list(data: dict, key: str, lang: str) -> list[str]:
    if lang == "zh" and data.get(f"{key}_zh"):
        return data[f"{key}_zh"]
    return data.get(key, [])


def chips(items: list[str]) -> str:
    return "".join(f'<span class="chip">{h(item)}</span>' for item in items)


def page_title(data: dict, lang: str, title_key: str) -> str:
    site = data["site"]
    site_title = site.get(f"title_{lang}", site["title"])
    title = t(data, lang, title_key)
    if title_key == "home":
        return site_title
    return f"{title} | {site_title}"


def nav(data: dict, lang: str, active: str, depth: int, page_path: str) -> str:
    root = rel_to_root(depth)
    labels = data["ui"][lang]["nav"]
    items = [
        ("home", ""),
        ("publications", "publications/"),
        ("media", "media/"),
        ("cv", "cv/"),
        ("data", "data/"),
    ]
    nav_items = []
    for key, path in items:
        aria = ' aria-current="page"' if key == active else ""
        nav_items.append(f'<a href="{root}{lang}/{path}"{aria}>{h(labels[key])}</a>')

    other = "zh" if lang == "en" else "en"
    switch_label = "中文" if lang == "en" else "EN"
    switch_href = f"{root}{other}/{page_path}"
    nav_items.append(f'<a class="language-link" href="{switch_href}">{switch_label}</a>')
    return "\n".join(nav_items)


def layout(
    data: dict,
    lang: str,
    title_key: str,
    active: str,
    page_path: str,
    body: str,
    depth: int,
) -> str:
    root = rel_to_root(depth)
    site = data["site"]
    profile = data["profile"]
    brand_primary, brand_secondary = brand_name(profile, lang)
    description = site.get(f"description_{lang}", site["description"])
    html_lang = "zh-CN" if lang == "zh" else "en"
    skip = t(data, lang, "skip")
    return f"""<!doctype html>
<html lang="{html_lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{h(description)}">
  <title>{h(page_title(data, lang, title_key))}</title>
  <link rel="stylesheet" href="{root}assets/styles.css">
</head>
<body>
  <a class="skip-link" href="#main">{h(skip)}</a>
  <header class="site-header">
    <div class="wrap header-inner">
      <a class="brand" href="{root}{lang}/">
        <span class="brand-mark">CL</span>
        <span>
          <strong>{h(brand_primary)}</strong>
          <small>{h(brand_secondary)}</small>
        </span>
      </a>
      <nav class="main-nav" aria-label="{h(t(data, lang, "main_navigation"))}">
        {nav(data, lang, active, depth, page_path)}
      </nav>
    </div>
  </header>
  <main id="main">
    {body}
  </main>
  <footer class="site-footer">
    <div class="wrap footer-grid">
      <p>{h(t(data, lang, "footer_source"))} <code>data/site.json</code>.</p>
      <p>{h(t(data, lang, "last_updated"))}: {h(site["last_updated"])}</p>
    </div>
  </footer>
</body>
</html>
"""


def computed_metrics(data: dict, lang: str) -> list[dict]:
    pubs = data["publications"]
    conferences = data["conferences"]
    projects = data["projects"]
    labels = data["ui"][lang]["metrics"]
    ssci = sum(1 for pub in pubs if "SSCI" in pub.get("tags", []))
    cssci = sum(1 for pub in pubs if any("CSSCI" in tag for tag in pub.get("tags", [])))
    return [
        {"value": ssci, "label": labels["ssci"]},
        {"value": cssci, "label": labels["cssci"]},
        {"value": len(conferences), "label": labels["conference"]},
        {"value": len(projects), "label": labels["project"]},
    ]


def stat_block(data: dict, lang: str) -> str:
    return "\n".join(
        f"""<div class="stat">
          <strong>{h(item["value"])}</strong>
          <span>{h(item["label"])}</span>
        </div>"""
        for item in computed_metrics(data, lang)
    )


def profile_actions(data: dict, lang: str, depth: int) -> str:
    profile = data["profile"]
    actions = [link(local_url(profile["cv"], depth), t(data, lang, "download_cv"), "button primary")]
    for item in profile["links"]:
        label = item.get(f"label_{lang}", item["label"])
        actions.append(link(item["url"], label, "button ghost"))
    return "".join(actions)


def pub_card(data: dict, pub: dict, lang: str, depth: int, compact: bool = False) -> str:
    title_cn = pub.get("title_cn")
    cn_html = f'<p class="pub-cn">{h(title_cn)}</p>' if title_cn else ""
    tag_html = chips(pub.get("tags", []))
    actions = []
    if pub.get("url"):
        actions.append(link(local_url(pub["url"], depth), t(data, lang, "pdf"), "text-link"))
    if pub.get("slides"):
        actions.append(link(local_url(pub["slides"], depth), t(data, lang, "slides"), "text-link"))
    action_html = f'<div class="card-actions">{"".join(actions)}</div>' if actions else ""
    compact_class = " compact" if compact else ""
    return f"""<article class="pub-card{compact_class}">
      <div class="pub-year">{h(pub["year"])}</div>
      <div>
        <h3>{h(pub["title"])}</h3>
        {cn_html}
        <p class="pub-meta">{h(pub["authors"])} · <em>{h(item_text(pub, "venue", lang))}</em> {h(pub.get("status", ""))}</p>
        <div class="chip-row">{tag_html}</div>
        {action_html}
      </div>
    </article>"""


def timeline(data: dict, items: list[dict], lang: str) -> str:
    rows = []
    for item in items:
        rows.append(
            f"""<article class="timeline-item">
              <div class="timeline-date">{h(item_text(item, "period", lang))}</div>
              <div>
                <h3>{h(item_text(item, "degree", lang))}</h3>
                <p>{h(item_text(item, "institution", lang))} · {h(item_text(item, "location", lang))}</p>
                <small>{h(item_text(item, "details", lang))}</small>
              </div>
            </article>"""
        )
    return "\n".join(rows)


def section(title: str, eyebrow: str, content: str, classes: str = "") -> str:
    class_attr = f" {classes}" if classes else ""
    return f"""<section class="wrap content-section{class_attr}">
      <div class="section-heading tight">
        <p class="eyebrow">{h(eyebrow)}</p>
        <h2>{h(title)}</h2>
      </div>
      {content}
    </section>"""


def media_card(data: dict, item: dict, lang: str, depth: int) -> str:
    root = rel_to_root(depth)
    href = f'{root}{lang}/media/{item["id"]}/'
    action = t(data, lang, "watch") if item.get("video") else t(data, lang, "open")
    return f"""<article class="media-card">
      <a class="media-thumb" href="{href}" aria-label="{h(action)} {h(item["title"])}">
        <span>{h(item_text(item, "type", lang))}</span>
      </a>
      <div class="media-copy">
        <p class="eyebrow">{h(item["date"])} · {h(item_text(item, "location", lang))}</p>
        <h3><a href="{href}">{h(item["title"])}</a></h3>
        <p>{h(item_text(item, "summary", lang))}</p>
      </div>
    </article>"""


def conference_rows(data: dict, lang: str, depth: int) -> str:
    rows = []
    for item in data["conferences"]:
        actions = []
        if item.get("paper_url"):
            actions.append(link(local_url(item["paper_url"], depth), t(data, lang, "paper"), "text-link"))
        if item.get("slides_url"):
            actions.append(link(local_url(item["slides_url"], depth), t(data, lang, "slides"), "text-link"))
        action_html = f'\n                <div class="card-actions">{"".join(actions)}</div>' if actions else ""
        note = item.get("note") or item.get("award")
        title_cn_html = f'\n                <p class="pub-cn">{h(item["title_cn"])}</p>' if item.get("title_cn") else ""
        note_html = f"\n                <small>{h(note)}</small>" if note else ""
        rows.append(
            f"""<article class="conference-row">
              <strong>{h(item["year"])}</strong>
              <div>
                <h3>{h(item["title"])}</h3>{title_cn_html}
                <p>{h(item["authors"])} · <em>{h(item_text(item, "venue", lang))}</em> · {h(item_text(item, "location", lang))}</p>{note_html}{action_html}
              </div>
            </article>"""
        )
    return "\n".join(rows)


def list_items(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{h(item)}</li>" for item in items) + "</ul>"


def object_list(items: list[dict], lang: str, title_field: str = "title") -> str:
    rows = []
    for item in items:
        detail_parts = [
            part
            for part in (
                item_text(item, "type", lang),
                item_text(item, "role", lang),
                item_text(item, "period", lang),
            )
            if part
        ]
        detail = " · ".join(detail_parts)
        description_text = item_text(item, "description", lang)
        description = f"<p>{h(description_text)}</p>" if description_text else ""
        detail_html = f"<br><span>{h(detail)}</span>" if detail else ""
        rows.append(f"<li><strong>{h(item_text(item, title_field, lang))}</strong>{detail_html}{description}</li>")
    return "<ul>" + "".join(rows) + "</ul>"


def render_home(data: dict, lang: str) -> str:
    profile = data["profile"]
    ui = data["ui"][lang]
    depth = 1
    links = profile_actions(data, lang, depth)
    interests = profile.get(f"research_interests_{lang}", profile["research_interests"])
    hero_primary, hero_secondary = hero_name(profile, lang)
    themes = "\n".join(
        f"""<article class="theme">
          <h3>{h(item_text(item, "name", lang))}</h3>
          <p>{h(item_text(item, "text", lang))}</p>
        </article>"""
        for item in data["themes"]
    )
    pubs = "".join(pub_card(data, pub, lang, depth, compact=True) for pub in data["publications"])
    media = "".join(media_card(data, item, lang, depth) for item in data["media"])
    body = f"""<section class="hero">
      <div class="wrap hero-grid">
        <div class="hero-copy">
          <p class="eyebrow">{h(item_text(profile, "title", lang))} · {h(item_text(profile, "affiliation", lang))}</p>
          <h1>{h(hero_primary)} <span>{h(hero_secondary)}</span></h1>
          <p class="lead">{h(item_text(profile, "summary", lang))}</p>
          <div class="button-row">{links}</div>
          <div class="research-tags">{chips(interests)}</div>
        </div>
        <aside class="profile-panel" aria-label="{h(ui["profile_summary"])}">
          <img src="{h(local_url(profile["photo"], depth))}" alt="{h(profile["preferred"])} portrait">
          <div>
            <h2>{h(profile_card_name(profile, lang))}</h2>
            <p>{h(item_text(profile, "location", lang))}</p>
            <a class="text-link" href="mailto:{h(profile["email"])}">{h(profile["email"])}</a>
          </div>
        </aside>
      </div>
    </section>
    <section class="wrap stats-grid" aria-label="{h(ui["academic_highlights"])}">
      {stat_block(data, lang)}
    </section>
    {section(ui["education"], ui["education_eyebrow"], f'<div class="timeline">{timeline(data, data["education"], lang)}</div>', "education-first")}
    <section class="band">
      <div class="wrap section-heading">
        <p class="eyebrow">{h(ui["research_areas"])}</p>
        <h2>{h(ui["research_blurb"])}</h2>
      </div>
      <div class="wrap theme-grid">{themes}</div>
    </section>
    {section(ui["publications"], ui["publications_eyebrow"], f'<div class="pub-list">{pubs}</div><p class="section-link"><a href="publications/">{h(ui["view_publications"])}</a></p>')}
    {section(ui["conference_presentations"], ui["conference_eyebrow"], f'<div class="conference-list">{conference_rows(data, lang, depth)}</div>')}
    {section(ui["working_papers"], ui["working_eyebrow"], list_items(localized_list(data, "working_papers", lang)), "prose-section")}
    {section(ui["research_projects"], ui["projects_eyebrow"], object_list(data["projects"], lang), "prose-section")}
    {section(ui["media_work"], ui["media_eyebrow"], f'<div class="media-grid wide">{media}</div><p class="section-link"><a href="media/">{h(ui["view_media"])}</a></p>')}
    {section(ui["professional_experience"], ui["experience_eyebrow"], object_list(data["experience"], lang, "organization"), "prose-section")}
    {section(ui["teaching"], ui["teaching_eyebrow"], list_items(localized_list(data, "teaching", lang)), "prose-section")}
    {section(ui["honors"], ui["honors_eyebrow"], list_items(localized_list(data, "honors", lang)), "prose-section")}
    {section(ui["skills"], ui["skills_eyebrow"], "<ul>" + "".join(f"<li><strong>{h(item_text(item, 'category', lang))}:</strong> {h(item_text(item, 'items', lang))}</li>" for item in data["skills"]) + "</ul>", "prose-section")}
    {section(ui["contact"], ui["contact_eyebrow"], f'<p><a href="mailto:{h(profile["email"])}">{h(profile["email"])}</a></p><div class="button-row">{profile_actions(data, lang, depth)}</div>', "prose-section")}
    """
    return layout(data, lang, "home", "home", "", body, depth)


def render_publications(data: dict, lang: str) -> str:
    ui = data["ui"][lang]
    depth = 2
    publications = "".join(pub_card(data, pub, lang, depth) for pub in data["publications"])
    working = list_items(localized_list(data, "working_papers", lang))
    body = f"""<section class="page-hero wrap">
      <p class="eyebrow">{h(ui["publications"])}</p>
      <h1>{h(ui["publications_title"])}</h1>
      <p>{h(ui["publications_intro"])}</p>
    </section>
    <section class="wrap pub-list">{publications}</section>
    <section class="band">
      <div class="wrap section-heading tight">
        <p class="eyebrow">{h(ui["conference_presentations"])}</p>
        <h2>{h(ui["conference_title"])}</h2>
      </div>
      <div class="wrap conference-list">{conference_rows(data, lang, depth)}</div>
    </section>
    <section class="wrap prose-block">
      <p class="eyebrow">{h(ui["working_papers"])}</p>
      {working}
    </section>"""
    return layout(data, lang, "publications", "publications", "publications/", body, depth)


def render_media_index(data: dict, lang: str) -> str:
    ui = data["ui"][lang]
    depth = 2
    body = f"""<section class="page-hero wrap">
      <p class="eyebrow">{h(ui["media"])}</p>
      <h1>{h(ui["media_title"])}</h1>
      <p>{h(ui["media_intro"])}</p>
    </section>
    <section class="wrap media-grid wide">
      {''.join(media_card(data, item, lang, depth) for item in data["media"])}
    </section>"""
    return layout(data, lang, "media", "media", "media/", body, depth)


def render_media_detail(data: dict, lang: str, item: dict) -> str:
    ui = data["ui"][lang]
    depth = 3
    if item.get("video"):
        player = f"""<video controls preload="metadata" playsinline>
          <source src="{h(item["video"])}" type="video/mp4">
          {h(ui["video_fallback"])}
        </video>"""
    else:
        player = f"""<div class="external-panel">
          <p>{h(ui["external_media"])}</p>
          {link(item.get("external_url", ""), ui["open_playback"], "button primary")}
        </div>"""
    body = f"""<section class="page-hero wrap media-detail-heading">
      <p class="eyebrow">{h(item_text(item, "type", lang))} · {h(item["date"])}</p>
      <h1>{h(item["title"])}</h1>
      <p>{h(item_text(item, "summary", lang))}</p>
    </section>
    <section class="wrap media-detail">
      {player}
      <aside>
        <h2>{h(ui["details"])}</h2>
        <dl>
          <dt>{h(ui["venue"])}</dt><dd>{h(item["venue"])}</dd>
          <dt>{h(ui["location"])}</dt><dd>{h(item_text(item, "location", lang))}</dd>
          <dt>{h(ui["date"])}</dt><dd>{h(item["date"])}</dd>
        </dl>
        <a class="text-link" href="../">{h(ui["back_to_media"])}</a>
      </aside>
    </section>"""
    return layout(data, lang, "media", "media", f'media/{item["id"]}/', body, depth)


def render_cv(data: dict, lang: str) -> str:
    profile = data["profile"]
    ui = data["ui"][lang]
    depth = 2
    pubs = "".join(pub_card(data, pub, lang, depth, compact=True) for pub in data["publications"])
    body = f"""<section class="page-hero wrap cv-heading">
      <p class="eyebrow">{h(ui["cv"])}</p>
      <h1>{h(profile["name"])} / {h(profile["name_cn"])}</h1>
      <p>{h(item_text(profile, "affiliation", lang))} · <a href="mailto:{h(profile["email"])}">{h(profile["email"])}</a></p>
      <div class="button-row">{link(local_url(profile["cv"], depth), ui["download_pdf_cv"], "button primary")}</div>
    </section>
    <section class="wrap cv-grid">
      <aside class="cv-sidebar">
        <h2>{h(ui["education"])}</h2>
        <div class="timeline">{timeline(data, data["education"], lang)}</div>
        <h2>{h(ui["languages"])}</h2>
        <p>{h(", ".join(item_text(profile, "languages", lang) if isinstance(item_text(profile, "languages", lang), list) else profile["languages"]))}</p>
      </aside>
      <div class="cv-main">
        <section><h2>{h(ui["publications"])}</h2><div class="pub-list">{pubs}</div></section>
        <section><h2>{h(ui["conference_presentations"])}</h2><div class="conference-list">{conference_rows(data, lang, depth)}</div></section>
        <section><h2>{h(ui["working_papers"])}</h2>{list_items(localized_list(data, "working_papers", lang))}</section>
        <section><h2>{h(ui["research_projects"])}</h2>{object_list(data["projects"], lang)}</section>
        <section><h2>{h(ui["professional_experience"])}</h2>{object_list(data["experience"], lang, "organization")}</section>
        <section><h2>{h(ui["teaching"])}</h2>{list_items(localized_list(data, "teaching", lang))}</section>
        <section><h2>{h(ui["honors"])}</h2>{list_items(localized_list(data, "honors", lang))}</section>
        <section><h2>{h(ui["skills"])}</h2><ul>{"".join(f"<li><strong>{h(item_text(item, 'category', lang))}:</strong> {h(item_text(item, 'items', lang))}</li>" for item in data["skills"])}</ul></section>
      </div>
    </section>"""
    return layout(data, lang, "cv", "cv", "cv/", body, depth)


def render_data(data: dict, lang: str) -> str:
    ui = data["ui"][lang]
    depth = 2
    cards = []
    for item in data.get("data_resources", []):
        if item.get("visibility") == "private":
            continue
        files = []
        for file_item in item.get("files", []):
            label = file_item.get(f"label_{lang}", file_item.get("label", ui["file"]))
            files.append(f'                <li>{link(local_url(file_item["url"], depth), label, "resource-link")}</li>')
        file_rows = "\n".join(files)
        file_html = f'\n              <ul class="resource-files">\n{file_rows}\n              </ul>' if files else ""
        actions = []
        if item.get("external_url"):
            actions.append(link(item["external_url"], ui["external_link"], "text-link"))
        action_html = f'\n              <div class="card-actions">{"".join(actions)}</div>' if actions else ""
        cards.append(
            f"""<article class="resource-card">
              <div>
                <p class="eyebrow">{h(item_text(item, "type", lang))} · {h(str(item.get("year", "")))}</p>
                <h3>{h(item_text(item, "title", lang))}</h3>
                <p>{h(item_text(item, "project", lang))}</p>
                <p>{h(item_text(item, "description", lang))}</p>
              </div>{file_html}{action_html}
            </article>"""
        )
    body = f"""<section class="page-hero wrap">
      <p class="eyebrow">{h(ui["data"])}</p>
      <h1>{h(ui["data_title"])}</h1>
      <p>{h(ui["data_intro"])}</p>
    </section>
    <section class="wrap resource-grid">
      {''.join(cards)}
    </section>"""
    return layout(data, lang, "data", "data", "data/", body, depth)


def render_root(data: dict) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="0; url=en/">
  <title>{h(data["site"]["title"])}</title>
  <link rel="stylesheet" href="assets/styles.css">
</head>
<body>
  <main class="root-choice wrap">
    <h1>{h(data["site"]["title"])}</h1>
    <p><a class="button primary" href="en/">English</a> <a class="button ghost" href="zh/">中文</a></p>
  </main>
</body>
</html>
"""


def clean_docs() -> None:
    if DOCS.exists():
        shutil.rmtree(DOCS)
    DOCS.mkdir(parents=True)


def copy_assets() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    for path in SRC_ASSETS.iterdir():
        target = ASSETS / path.name
        if path.is_file():
            shutil.copy2(path, target)
        elif path.is_dir():
            shutil.copytree(path, target)


def build() -> None:
    data = read_data()
    clean_docs()
    copy_assets()
    write(DOCS / "index.html", render_root(data))
    for lang in LANGS:
        write(DOCS / lang / "index.html", render_home(data, lang))
        write(DOCS / lang / "publications" / "index.html", render_publications(data, lang))
        write(DOCS / lang / "media" / "index.html", render_media_index(data, lang))
        for item in data["media"]:
            write(DOCS / lang / "media" / item["id"] / "index.html", render_media_detail(data, lang, item))
        write(DOCS / lang / "cv" / "index.html", render_cv(data, lang))
        write(DOCS / lang / "data" / "index.html", render_data(data, lang))


if __name__ == "__main__":
    build()
