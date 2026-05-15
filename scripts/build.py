#!/usr/bin/env python3
"""Build the static academic site from data/site.json."""

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


def h(value: object) -> str:
    return escape(str(value), quote=True)


def read_data() -> dict:
    with DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def rel_to_root(depth: int) -> str:
    return "../" * depth


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def link(url: str, label: str, classes: str = "") -> str:
    if not url:
        return ""
    class_attr = f' class="{classes}"' if classes else ""
    return f'<a href="{h(url)}"{class_attr}>{h(label)}</a>'


def local_url(url: str, depth: int) -> str:
    if not url or url.startswith(("http://", "https://", "mailto:", "/")):
        return url
    return f"{rel_to_root(depth)}{url}"


def nav(active: str, root: str) -> str:
    items = [
        ("Home", "index.html", "home"),
        ("Publications", "publications/", "publications"),
        ("Media", "media/", "media"),
        ("CV", "cv/", "cv"),
    ]
    html = []
    for label, href, key in items:
        aria = ' aria-current="page"' if key == active else ""
        html.append(f'<a href="{root}{href}"{aria}>{label}</a>')
    return "\n".join(html)


def layout(data: dict, title: str, active: str, body: str, depth: int = 0) -> str:
    root = rel_to_root(depth)
    site = data["site"]
    full_title = site["title"] if title == "Home" else f"{title} | {site['title']}"
    description = h(site["description"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{description}">
  <title>{h(full_title)}</title>
  <link rel="stylesheet" href="{root}assets/styles.css">
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="wrap header-inner">
      <a class="brand" href="{root}index.html">
        <span class="brand-mark">CL</span>
        <span>
          <strong>Chris Lu</strong>
          <small>Lu Hongcheng</small>
        </span>
      </a>
      <nav class="main-nav" aria-label="Main navigation">
        {nav(active, root)}
      </nav>
    </div>
  </header>
  <main id="main">
    {body}
  </main>
  <footer class="site-footer">
    <div class="wrap footer-grid">
      <p>© {h(data["profile"]["preferred"])}. Built from <code>data/site.json</code>.</p>
      <p>Last updated: {h(site["last_updated"])}</p>
    </div>
  </footer>
</body>
</html>
"""


def chips(items: list[str]) -> str:
    return "".join(f'<span class="chip">{h(item)}</span>' for item in items)


def stat_block(data: dict) -> str:
    return "\n".join(
        f"""<div class="stat">
          <strong>{h(item["value"])}</strong>
          <span>{h(item["label"])}</span>
        </div>"""
        for item in data["metrics"]
    )


def pub_card(pub: dict, compact: bool = False, depth: int = 0) -> str:
    title_cn = pub.get("title_cn")
    cn_html = f'<p class="pub-cn">{h(title_cn)}</p>' if title_cn else ""
    tag_html = chips(pub.get("tags", []))
    action = link(local_url(pub.get("url", ""), depth), "PDF", "text-link")
    action_html = f'<div class="card-actions">{action}</div>' if action else ""
    compact_class = " compact" if compact else ""
    return f"""<article class="pub-card{compact_class}">
      <div class="pub-year">{h(pub["year"])}</div>
      <div>
        <h3>{h(pub["title"])}</h3>
        {cn_html}
        <p class="pub-meta">{h(pub["authors"])} · <em>{h(pub["venue"])}</em> {h(pub.get("status", ""))}</p>
        <div class="chip-row">{tag_html}</div>
        {action_html}
      </div>
    </article>"""


def timeline(items: list[dict]) -> str:
    rows = []
    for item in items:
        rows.append(
            f"""<article class="timeline-item">
              <div class="timeline-date">{h(item["period"])}</div>
              <div>
                <h3>{h(item["degree"])}</h3>
                <p>{h(item["institution"])} · {h(item["location"])}</p>
                <small>{h(item["details"])}</small>
              </div>
            </article>"""
        )
    return "\n".join(rows)


def media_card(item: dict, depth: int = 0) -> str:
    root = rel_to_root(depth)
    href = f'{root}media/{item["id"]}/'
    action = "Watch" if item.get("video") else "Open"
    return f"""<article class="media-card">
      <a class="media-thumb" href="{href}" aria-label="{h(action)} {h(item["title"])}">
        <span>{h(item["type"])}</span>
      </a>
      <div class="media-copy">
        <p class="eyebrow">{h(item["date"])} · {h(item["location"])}</p>
        <h3><a href="{href}">{h(item["title"])}</a></h3>
        <p>{h(item["summary"])}</p>
      </div>
    </article>"""


def render_home(data: dict) -> str:
    profile = data["profile"]
    selected = [p for p in data["publications"] if p.get("selected")][:5]
    recent_media = data["media"][:3]
    links = "\n".join(
        link(item["url"], item["label"], "button ghost") for item in profile["links"]
    )
    primary = link(profile["cv"], "Download CV", "button primary")
    themes = "\n".join(
        f"""<article class="theme">
          <h3>{h(item["name"])}</h3>
          <p>{h(item["text"])}</p>
        </article>"""
        for item in data["themes"]
    )
    body = f"""<section class="hero">
      <div class="wrap hero-grid">
        <div class="hero-copy">
          <p class="eyebrow">{h(profile["title"])} · {h(profile["affiliation"])}</p>
          <h1>{h(profile["preferred"])} <span>{h(profile["name"])}</span></h1>
          <p class="lead">{h(profile["summary"])}</p>
          <div class="button-row">{primary}{links}</div>
          <div class="research-tags">{chips(profile["research_interests"])}</div>
        </div>
        <aside class="profile-panel" aria-label="Profile summary">
          <img src="{h(profile["photo"])}" alt="{h(profile["preferred"])} portrait">
          <div>
            <h2>{h(profile["name_cn"])} / {h(profile["name"])}</h2>
            <p>{h(profile["location"])}</p>
            <a class="text-link" href="mailto:{h(profile["email"])}">{h(profile["email"])}</a>
          </div>
        </aside>
      </div>
    </section>
    <section class="wrap stats-grid" aria-label="Academic highlights">
      {stat_block(data)}
    </section>
    <section class="band">
      <div class="wrap section-heading">
        <p class="eyebrow">Research Areas</p>
        <h2>Focused enough to be legible, broad enough to travel.</h2>
      </div>
      <div class="wrap theme-grid">{themes}</div>
    </section>
    <section class="wrap two-column">
      <div>
        <div class="section-heading tight">
          <p class="eyebrow">Selected Publications</p>
          <h2>Recent work</h2>
        </div>
        <div class="pub-list">{''.join(pub_card(p, True) for p in selected)}</div>
        <p class="section-link"><a href="publications/">View all publications</a></p>
      </div>
      <div>
        <div class="section-heading tight">
          <p class="eyebrow">Education</p>
          <h2>Training</h2>
        </div>
        <div class="timeline">{timeline(data["education"])}</div>
      </div>
    </section>
    <section class="wrap">
      <div class="section-heading tight">
        <p class="eyebrow">Media Work</p>
        <h2>Video, live broadcast, and public communication.</h2>
      </div>
      <div class="media-grid">{''.join(media_card(m) for m in recent_media)}</div>
      <p class="section-link"><a href="media/">View all media work</a></p>
    </section>"""
    return layout(data, "Home", "home", body)


def render_publications(data: dict) -> str:
    publications = "\n".join(pub_card(pub, depth=1) for pub in data["publications"])
    conferences = "\n".join(
        f"""<article class="conference-row">
          <strong>{h(item["year"])}</strong>
          <div>
            <h3>{h(item["title"])}</h3>
            <p>{h(item["authors"])} · <em>{h(item["venue"])}</em> · {h(item["location"])}</p>
            {f'<small>{h(item["note"])}</small>' if item.get("note") else ''}
          </div>
        </article>"""
        for item in data["conferences"]
    )
    working = "".join(f"<li>{h(item)}</li>" for item in data["working_papers"])
    body = f"""<section class="page-hero wrap">
      <p class="eyebrow">Publications</p>
      <h1>Articles, conference papers, and manuscripts.</h1>
      <p>Journal entries are kept as structured records, so tags, PDFs, and selected-work flags can be updated in one place.</p>
    </section>
    <section class="wrap pub-list">{publications}</section>
    <section class="band">
      <div class="wrap section-heading tight">
        <p class="eyebrow">Conference Presentations</p>
        <h2>Talks and papers</h2>
      </div>
      <div class="wrap conference-list">{conferences}</div>
    </section>
    <section class="wrap prose-block">
      <p class="eyebrow">Working Papers</p>
      <ul>{working}</ul>
    </section>"""
    return layout(data, "Publications", "publications", body, depth=1)


def render_media_index(data: dict) -> str:
    body = f"""<section class="page-hero wrap">
      <p class="eyebrow">Media</p>
      <h1>Public-facing work across video, broadcast, and live platforms.</h1>
      <p>Videos use native browser playback with <code>preload="metadata"</code>, so opening the page should not trigger unwanted downloads.</p>
    </section>
    <section class="wrap media-grid wide">
      {''.join(media_card(item, depth=1) for item in data["media"])}
    </section>"""
    return layout(data, "Media", "media", body, depth=1)


def render_media_detail(data: dict, item: dict) -> str:
    if item.get("video"):
        player = f"""<video controls preload="metadata" playsinline>
          <source src="{h(item["video"])}" type="video/mp4">
          Your browser does not support the video tag.
        </video>"""
    else:
        player = f"""<div class="external-panel">
          <p>This item is hosted on an external platform.</p>
          {link(item.get("external_url", ""), "Open playback", "button primary")}
        </div>"""
    body = f"""<section class="page-hero wrap media-detail-heading">
      <p class="eyebrow">{h(item["type"])} · {h(item["date"])}</p>
      <h1>{h(item["title"])}</h1>
      <p>{h(item["summary"])}</p>
    </section>
    <section class="wrap media-detail">
      {player}
      <aside>
        <h2>Details</h2>
        <dl>
          <dt>Venue</dt><dd>{h(item["venue"])}</dd>
          <dt>Location</dt><dd>{h(item["location"])}</dd>
          <dt>Date</dt><dd>{h(item["date"])}</dd>
        </dl>
        <a class="text-link" href="../">Back to media</a>
      </aside>
    </section>"""
    return layout(data, item["title"], "media", body, depth=2)


def render_cv(data: dict) -> str:
    profile = data["profile"]
    projects = "".join(
        f"""<li><strong>{h(item["title"])}</strong><br><span>{h(item["type"])} · {h(item["period"])}</span></li>"""
        for item in data["projects"]
    )
    experience = "".join(
        f"""<li><strong>{h(item["organization"])}</strong>, {h(item["role"])}<br><span>{h(item["period"])} · {h(item["description"])}</span></li>"""
        for item in data["experience"]
    )
    teaching = "".join(f"<li>{h(item)}</li>" for item in data["teaching"])
    honors = "".join(f"<li>{h(item)}</li>" for item in data["honors"])
    skills = "".join(
        f"<li><strong>{h(item['category'])}:</strong> {h(item['items'])}</li>"
        for item in data["skills"]
    )
    pubs = "".join(pub_card(pub, True, depth=1) for pub in data["publications"])
    confs = "".join(
        f"<li>{h(item['authors'])} ({h(item['year'])}). {h(item['title'])}. <em>{h(item['venue'])}</em>, {h(item['location'])}.</li>"
        for item in data["conferences"]
    )
    body = f"""<section class="page-hero wrap cv-heading">
      <p class="eyebrow">Curriculum Vitae</p>
      <h1>{h(profile["name"])} / {h(profile["name_cn"])}</h1>
      <p>{h(profile["affiliation"])} · <a href="mailto:{h(profile["email"])}">{h(profile["email"])}</a></p>
      <div class="button-row">{link(local_url(profile["cv"], 1), "Download PDF CV", "button primary")}</div>
    </section>
    <section class="wrap cv-grid">
      <aside class="cv-sidebar">
        <h2>Education</h2>
        <div class="timeline">{timeline(data["education"])}</div>
        <h2>Languages</h2>
        <p>{h(", ".join(profile["languages"]))}</p>
      </aside>
      <div class="cv-main">
        <section><h2>Publications</h2><div class="pub-list">{pubs}</div></section>
        <section><h2>Conference Papers</h2><ul>{confs}</ul></section>
        <section><h2>Research Projects</h2><ul>{projects}</ul></section>
        <section><h2>Professional Experience</h2><ul>{experience}</ul></section>
        <section><h2>Teaching</h2><ul>{teaching}</ul></section>
        <section><h2>Awards & Honors</h2><ul>{honors}</ul></section>
        <section><h2>Skills</h2><ul>{skills}</ul></section>
      </div>
    </section>"""
    return layout(data, "CV", "cv", body, depth=1)


def copy_assets() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    for path in SRC_ASSETS.iterdir():
        if path.is_file():
            shutil.copy2(path, ASSETS / path.name)
        elif path.is_dir():
            target = ASSETS / path.name
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(path, target)


def build() -> None:
    data = read_data()
    DOCS.mkdir(exist_ok=True)
    copy_assets()
    write(DOCS / "index.html", render_home(data))
    write(DOCS / "publications" / "index.html", render_publications(data))
    write(DOCS / "media" / "index.html", render_media_index(data))
    for item in data["media"]:
        write(DOCS / "media" / item["id"] / "index.html", render_media_detail(data, item))
    write(DOCS / "cv" / "index.html", render_cv(data))


if __name__ == "__main__":
    build()
