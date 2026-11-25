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
        return profile["name_cn"], profile["preferred"]
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
        ("products", "products/"),
        ("media", "media/"),
        ("cv", "cv/"),
        ("data", "data/"),
    ]
    nav_items = []
    for key, path in items:
        if key == "media" and not data.get("show_media", True):
            continue
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
<body class="{'home-body' if active == 'home' else 'inner-body'}">
  <a class="skip-link" href="#main">{h(skip)}</a>
  <header class="site-header">
    <div class="wrap header-inner">
      <a class="brand" href="{root}{lang}/">
        <img class="brand-mark" src="{h(local_url(profile["photo"], depth))}" alt="{h(profile["preferred"])} portrait">
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
  <main id="main" class="{'home-page' if active == 'home' else 'inner-page'}">
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
    cv_url = item_text(profile, "cv", lang)
    actions = [link(local_url(cv_url, depth), t(data, lang, "download_cv"), "button primary")]
    for item in profile["links"]:
        label = item.get(f"label_{lang}", item["label"])
        actions.append(link(item["url"], label, "button ghost"))
    return "".join(actions)


def pub_card(data: dict, pub: dict, lang: str, depth: int, compact: bool = False) -> str:
    title_cn = pub.get("title_cn")
    title = title_cn if lang == "zh" and title_cn else pub["title"]
    secondary_title = pub["title"] if lang == "zh" and title_cn else title_cn
    cn_html = f'<p class="pub-cn">{h(secondary_title)}</p>' if secondary_title else ""
    tag_html = chips(pub.get("tags", []))
    actions = []
    if pub.get("url"):
        actions.append(link(local_url(pub["url"], depth), t(data, lang, "pdf"), "text-link"))
    if pub.get("doi"):
        actions.append(link(pub["doi"], "DOI", "text-link"))
    if pub.get("slides"):
        actions.append(link(local_url(pub["slides"], depth), t(data, lang, "slides"), "text-link"))
    action_html = f'<div class="card-actions">{"".join(actions)}</div>' if actions else ""
    meta_html = f'{h(item_text(pub, "authors", lang))} · <em>{h(item_text(pub, "venue", lang))}</em> {h(pub.get("status", ""))}'
    if pub.get("type") == "Book chapter" and pub.get("editors"):
        editors = h(item_text(pub, "editors", lang))
        container = f'<em>{h(item_text(pub, "venue", lang))}</em>'
        source = (f'载{editors}（主编），{container}（第{h(pub["pages"])}页）' if lang == "zh"
                  else f'In {editors} (Eds.), {container} (pp. {h(pub["pages"])})')
        meta_html = f'{h(item_text(pub, "authors", lang).rstrip("."))}. ({h(pub["year"])}). {h(title)}. {source}. {h(item_text(pub, "publisher", lang))}.'
    compact_class = " compact" if compact else ""
    return f"""<article class="pub-card{compact_class}">
      <div class="pub-year">{h(pub["year"])}</div>
      <div>
        <h3>{h(title)}</h3>
        {cn_html}
        <p class="pub-meta">{meta_html}</p>
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
    title = item_text(item, "title", lang)
    return f"""<article class="media-card">
      <a class="media-thumb" href="{href}" aria-label="{h(action)} {h(title)}">
        <span>{h(item_text(item, "type", lang))}</span>
      </a>
      <div class="media-copy">
        <p class="eyebrow">{h(item["date"])} · {h(item_text(item, "location", lang))}</p>
        <h3><a href="{href}">{h(title)}</a></h3>
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
        note = item_text(item, "note", lang) or item_text(item, "award", lang)
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


def theme_outcomes(data: dict, theme: dict, lang: str, depth: int) -> str:
    publications = {pub["id"]: pub for pub in data["publications"]}
    conferences = {item["title"]: item for item in data["conferences"]}
    rows = []
    for ref in theme.get("outcomes", []):
        if "publication_id" in ref:
            pub = publications[ref["publication_id"]]
            title = pub.get("title_cn", pub["title"]) if lang == "zh" else pub["title"]
            title_html = link(local_url(pub["url"], depth), title) if pub.get("url") else h(title)
            meta = f'{item_text(pub, "venue", lang)} · {pub["year"]}'
        elif "conference_title" in ref:
            item = conferences[ref["conference_title"]]
            title_html = h(item_text(item, "title", lang))
            kind = "会议报告" if lang == "zh" else "Conference presentation"
            meta = f'{kind} · {item["venue"]} · {item["year"]}'
            if item.get("note"):
                meta += f' · {item_text(item, "note", lang)}'
        else:
            title_html = h(localized_list(data, "working_papers", lang)[ref["working_paper_index"]])
            meta = "工作论文" if lang == "zh" else "Working paper"
        rows.append(f'<li>{title_html}<span class="outcome-meta">{h(meta)}</span></li>')
    label = "相关成果" if lang == "zh" else "Related work"
    return f'<h4 class="outcome-heading">{label}</h4><ul class="theme-outcomes">{"".join(rows)}</ul>' if rows else ""


def render_home(data: dict, lang: str) -> str:
    profile = data["profile"]
    ui = data["ui"][lang]
    depth = 1
    home = data["home"]
    links = link("publications/", "代表成果" if lang == "zh" else "Publications", "button primary")
    links += link("cv/", "完整简历" if lang == "zh" else "Full CV", "button ghost")
    conference_map = {item["title"]: item for item in data["conferences"]}
    conference_data = {**data, "conferences": [conference_map[title] for title in home["conference_titles"]]}
    conference_link = link("publications/#conferences", "查看全部会议成果" if lang == "zh" else "View all conference presentations", "text-link")
    publication_map = {pub["id"]: pub for pub in data["publications"]}
    interests = profile.get(f"research_interests_{lang}", profile["research_interests"])
    hero_primary, hero_secondary = hero_name(profile, lang)
    themes = "\n".join(
        f"""<article class="theme">
          <h3>{h(item_text(item, "name", lang))}</h3>
          <p>{h(item_text(item, "text", lang))}</p>
          {theme_outcomes(data, item, lang, depth)}
        </article>"""
        for item in data["themes"]
    )
    pubs = "".join(pub_card(data, pub, lang, depth, compact=True) for pub in (publication_map[pub_id] for pub_id in home["publication_ids"]))
    media = "".join(media_card(data, item, lang, depth) for item in data["media"][:2])
    language_label = "工作语言" if lang == "zh" else "Working languages"
    language_items = profile.get(f"working_languages_{lang}", profile["working_languages"])
    language_list = "".join(f"<li>{h(item)}</li>" for item in language_items)
    summary_html = f'<p>{h(item_text(profile, "summary", lang))}</p>'
    product_previews = "".join(
        f'<article class="product-preview"><a href="{h(item["url"])}" target="_blank" rel="noopener"><img src="{h(local_url(item["image"], depth))}" alt="{h(item_text(item, "title", lang))}" loading="lazy"><h3>{h(item_text(item, "title", lang))}</h3></a><p>{h(item_text(item, "tagline", lang))}</p></article>'
        for item in data.get("products", [])
    )
    product_link = link("products/", "查看全部研究产品" if lang == "zh" else "View all research products", "text-link")
    media_section = section(ui["media_work"], ui["media_eyebrow"], f'<div class="media-grid wide">{media}</div><p class="section-link"><a href="media/">{h(ui["view_media"])}</a></p>') if data.get("show_media", True) else ""
    body = f"""<section class="hero">
      <div class="wrap hero-grid intro-panel">
        <div class="hero-copy">
          <h1>{h(hero_primary)} <span>{h(hero_secondary)}</span></h1>
          <p class="hero-affiliation">{h(item_text(profile, "affiliation", lang))} · {h(item_text(profile, "title", lang))}</p>
          <div class="hero-bio">{summary_html}</div>
        </div>
        <aside class="profile-panel" aria-label="{h(ui["profile_summary"])}">
          <img src="{h(local_url(profile["photo"], depth))}" alt="{h(profile["preferred"])} portrait">
          <div>
            <p>{h(item_text(profile, "location", lang))}</p>
            <a class="text-link" href="mailto:{h(profile["email"])}">{h(profile["email"])}</a>
          </div>
        </aside>
        <div class="hero-footer">
          <div class="hero-details">
            <div class="research-tags">{chips(interests)}</div>
            <div class="working-languages" aria-label="{h(language_label)}">
              <strong>{h(language_label)}</strong><ul>{language_list}</ul>
            </div>
          </div>
          <div class="button-row">{links}</div>
        </div>
      </div>
    </section>
    <section class="band research-band">
      <div class="wrap section-heading">
        <p class="eyebrow">{h(ui["research_areas"])}</p>
        <h2>{h(ui["research_blurb"])}</h2>
      </div>
      <p class="wrap research-scroll-hint">{"左右滑动查看研究方向" if lang == "zh" else "Scroll horizontally to explore research areas"}</p>
      <div class="wrap theme-grid" tabindex="0" role="region" aria-label="{h(ui['research_areas'])}">{themes}</div>
    </section>
    {section("论文发表" if lang == "zh" else "Publications", "代表成果" if lang == "zh" else "Selected work", f'<div class="pub-list">{pubs}</div><p class="section-link"><a href="publications/">{h(ui["view_publications"])}</a></p>')}
    {section("会议发表" if lang == "zh" else "Conference presentations", "四大会议 · 第一作者" if lang == "zh" else "ICA · AEJMC · IAMCR · NCA · First author", f'<div class="conference-list">{conference_rows(conference_data, lang, depth)}</div><p class="section-link">{conference_link}</p>')}
    {section("研究产品" if lang == "zh" else "Research products", "交互看板" if lang == "zh" else "Interactive dashboards", f'<div class="product-previews">{product_previews}</div><p class="section-link">{product_link}</p>')}
    {section(ui["honors"], ui["honors_eyebrow"], list_items(localized_list(data, "honors", lang)), "prose-section")}
    {media_section}
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
    <section class="band" id="conferences">
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
      <h1>{h(item_text(item, "title", lang))}</h1>
      <p>{h(item_text(item, "summary", lang))}</p>
    </section>
    <section class="wrap media-detail">
      {player}
      <aside>
        <h2>{h(ui["details"])}</h2>
        <dl>
          <dt>{h(ui["venue"])}</dt><dd>{h(item_text(item, "venue", lang))}</dd>
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
      <div class="button-row">{link(local_url(item_text(profile, "cv", lang), depth), ui["download_pdf_cv"], "button primary")}</div>
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


def product_card(data: dict, item: dict, lang: str, depth: int, featured: bool = False) -> str:
    ui = data["ui"][lang]
    tags = item.get(f"tags_{lang}", item.get("tags", []))
    highlights = item.get(f"highlights_{lang}", item.get("highlights", []))
    bullets = "".join(f"<li>{h(x)}</li>" for x in highlights)
    cls = "product-card featured" if featured else "product-card"
    return f"""<article class="{cls}">
      <a class="product-shot" href="{h(item["url"])}" target="_blank" rel="noopener">
        <img src="{h(local_url(item["image"], depth))}" alt="{h(item_text(item, "title", lang))}" loading="lazy">
      </a>
      <div class="product-body">
        <p class="eyebrow">{h(item_text(item, "status", lang))}</p>
        <h3>{h(item_text(item, "title", lang))}</h3>
        <p class="product-tagline">{h(item_text(item, "tagline", lang))}</p>
        <ul class="product-points">{bullets}</ul>
        <div class="research-tags">{chips(tags)}</div>
        <div class="button-row">
          <a class="button primary" href="{h(item["url"])}" target="_blank" rel="noopener">{h(item.get("open_label_" + lang) or item.get("open_label") or ui["open_product"]) if lang != "en" else h(item.get("open_label") or ui["open_product"])}</a>
          <a class="button ghost" href="{h(item["methods_url"])}" target="_blank" rel="noopener">{h(ui["product_methods"])}</a>
        </div>
      </div>
    </article>"""


def render_products(data: dict, lang: str) -> str:
    ui = data["ui"][lang]
    depth = 2
    blocks = []
    for item in data.get("products", []):
        blocks.append(f"""{product_card(data, item, lang, depth, featured=True)}""")
    body = f"""<section class="page-hero wrap">
      <p class="eyebrow">{h(ui["products_eyebrow"])}</p>
      <h1>{h(ui["products_title"])}</h1>
      <p>{h(ui["products_intro"])}</p>
    </section>
    <section class="wrap product-list">
      {''.join(blocks)}
    </section>"""
    return layout(data, lang, "products", "products", "products/", body, depth)


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
        write(DOCS / lang / "products" / "index.html", render_products(data, lang))
        write(DOCS / lang / "cv" / "index.html", render_cv(data, lang))
        write(DOCS / lang / "data" / "index.html", render_data(data, lang))


if __name__ == "__main__":
    build()
