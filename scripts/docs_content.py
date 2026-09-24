"""Render checkpoint views, chips, questions, and diagrams for guide pages.

Standard library only. The MkDocs hook passes a relative-URL function; generate_docs.py
uses validate() so CI fails on broken checkpoint data without building the site.
"""
from __future__ import annotations
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs-data"
CHECKPOINT_COUNT = 36
SCORECARD = "scorecard/"
MARKER = re.compile(r"^<!--\s*(checkpoints|scorecard|diagram):\s*(.*?)\s*-->\s*$", re.M)


class ContentError(ValueError):
    """Documentation data or markers are inconsistent."""


def load():
    return json.loads((DATA / "checkpoints.json").read_text())


def validate(data=None):
    data = data or load()
    statuses, phases = data["statuses"], {p["id"] for p in data["phases"]}
    problems, seen = [], set()
    rows = data["checkpoints"]
    if len(rows) != CHECKPOINT_COUNT:
        problems.append(f"expected {CHECKPOINT_COUNT} checkpoints, found {len(rows)}")
    for row in rows:
        if row["id"] in seen:
            problems.append(f"duplicate checkpoint {row['id']}")
        seen.add(row["id"])
        if row["status"] not in statuses:
            problems.append(f"{row['id']}: unknown status {row['status']}")
        if row["phase"] not in phases:
            problems.append(f"{row['id']}: unknown phase {row['phase']}")
        for key in ("title", "how", "remains"):
            if not row.get(key):
                problems.append(f"{row['id']}: missing {key}")
    for item in data["checkpoints"] + data["beyond_rubric"]:
        if not item.get("evidence"):
            problems.append(f"{item.get('id')}: evidence is required")
        for path in item.get("evidence", []):
            if not (ROOT / path).is_file():
                problems.append(f"{item.get('id')}: evidence path does not exist: {path}")
    for item in data["frontier"]:
        for ident in item["checkpoints"]:
            if ident not in seen:
                problems.append(f"frontier {item['title']}: unknown checkpoint {ident}")
    diagrams = DATA / "diagrams"
    for source in sorted(diagrams.glob("*.mmd")):
        if not source.with_suffix(".html").is_file():
            problems.append(f"diagram {source.stem} has no rendered .html")
    for rendered in sorted(diagrams.glob("*.html")):
        if not rendered.with_suffix(".mmd").is_file():
            problems.append(f"diagram {rendered.stem} has no .mmd source")
    if problems:
        raise ContentError("Checkpoint data is invalid:\n" + "\n".join(problems))
    return data


def inline(text):
    """Escape text and render `code` spans."""
    parts = re.split(r"`([^`]+)`", text)
    return "".join(f"<code>{html.escape(p)}</code>" if i % 2 else html.escape(p) for i, p in enumerate(parts))


def anchor(ident):
    return ident.lower()


def counts(data):
    result = {key: 0 for key in data["statuses"]}
    for row in data["checkpoints"]:
        result[row["status"]] += 1
    return result


def chip(row, data, link):
    status = data["statuses"][row["status"]]["label"]
    title = html.escape(f"{row['id']} · {row['title']} · {status}", quote=True)
    return (f'<a class="checkpoint-chip checkpoint-chip--{row["status"]}" href="{link(SCORECARD)}#{anchor(row["id"])}" '
            f'title="{title}">{row["id"]}</a>')


def chips(value, data, link):
    index = {row["id"]: row for row in data["checkpoints"]}
    ids = [x.strip() for x in value.split(",") if x.strip()]
    unknown = [x for x in ids if x not in index]
    if unknown or not ids:
        raise ContentError(f"Unknown checkpoint chip(s): {unknown or value}")
    return ('<p class="checkpoint-chips"><span>Checkpoints</span> '
            + " ".join(chip(index[x], data, link) for x in ids) + "</p>")


def legend(data):
    total = counts(data)
    items = "".join(f'<li><span class="checkpoint-swatch checkpoint-swatch--{key}" aria-hidden="true"></span>'
                    f'{html.escape(value["label"])} <strong>{total[key]}</strong></li>'
                    for key, value in data["statuses"].items())
    return f'<ul class="checkpoint-legend" aria-label="Status counts">{items}</ul>'


def grid(data, link):
    rows = []
    for phase in data["phases"]:
        cells = "".join(
            f'<a class="checkpoint-cell checkpoint-cell--{row["status"]}" href="{link(SCORECARD)}#{anchor(row["id"])}" '
            f'title="{html.escape(row["title"] + " · " + data["statuses"][row["status"]]["label"], quote=True)}">'
            f'<span>{row["id"]}</span><span class="sr-only"> {html.escape(row["title"])}, '
            f'{html.escape(data["statuses"][row["status"]]["label"])}</span></a>'
            for row in data["checkpoints"] if row["phase"] == phase["id"])
        rows.append(f'<div class="checkpoint-grid__row"><p class="checkpoint-grid__phase">{html.escape(phase["label"])}</p>'
                    f'<div class="checkpoint-grid__cells">{cells}</div></div>')
    return (f'<div class="checkpoint-grid" aria-label="{CHECKPOINT_COUNT} checkpoints by status">' + "".join(rows)
            + "</div>" + legend(data))


def glance(data):
    total = counts(data)
    lines = ["| Status | Count | Meaning |", "|---|---:|---|"]
    lines += [f"| {value['label']} | {total[key]} | {value['meaning']} |" for key, value in data["statuses"].items()]
    return "\n".join(lines)


def status_pill(key, data):
    return f'<span class="status-pill status-pill--{key}">{html.escape(data["statuses"][key]["label"])}</span>'


def phase_tables(data):
    out = []
    for number, phase in enumerate(data["phases"], 1):
        rows = [row for row in data["checkpoints"] if row["phase"] == phase["id"]]
        body = "".join(
            f'<tr id="{anchor(row["id"])}"><td><code>{row["id"]}</code><br>{html.escape(row["title"])}</td>'
            f'<td>{status_pill(row["status"], data)}</td><td>{inline(row["how"])}</td><td>{inline(row["remains"])}</td></tr>'
            for row in rows)
        out.append(f"## {number}. {phase['label']}\n\n"
                   '<table class="scorecard-table"><thead><tr><th>Checkpoint</th><th>Status</th>'
                   "<th>How Stagecoach addresses it</th><th>What remains</th></tr></thead>"
                   f"<tbody>{body}</tbody></table>\n")
    return "\n".join(out)


def checklist(data, link):
    out = []
    for phase in data["phases"]:
        items = "".join(
            f'<li><a href="{link(SCORECARD)}#{anchor(row["id"])}"><code>{row["id"]}</code></a> '
            f'{html.escape(row["title"])} {status_pill(row["status"], data)}</li>'
            for row in data["checkpoints"] if row["phase"] == phase["id"])
        out.append(f"### {phase['label']}\n\n<ul class=\"checkpoint-list\">{items}</ul>\n")
    return "\n".join(out)


def beyond(data):
    cards = "".join(f'<div class="beyond-card" id="beyond-{item["id"]}"><h3>{html.escape(item["title"])}</h3>'
                    f"<p>{inline(item['why'])}</p></div>" for item in data["beyond_rubric"])
    return f'<div class="beyond-grid">{cards}</div>'


def beyond_chips(data, link):
    items = "".join(f'<a href="{link(SCORECARD)}#beyond-{item["id"]}">{html.escape(item["title"])}</a>'
                    for item in data["beyond_rubric"])
    return f'<div class="beyond-chips">{items}</div>'


def frontier(data, link):
    rows = "".join(
        f"<li><strong>{html.escape(item['title'])}</strong> "
        + " ".join(f'<a class="checkpoint-chip" href="{link(SCORECARD)}#{anchor(x)}">{x}</a>' for x in item["checkpoints"])
        + f"<br>{inline(item['detail'])}</li>" for item in data["frontier"])
    return f'<ul class="frontier-list">{rows}</ul>'


def diagram(name):
    if not re.fullmatch(r"[a-z0-9-]+", name):
        raise ContentError(f"Invalid diagram name: {name}")
    path = DATA / "diagrams" / f"{name}.html"
    if not path.is_file():
        raise ContentError(f"Unknown diagram: {name}")
    # Collapse to one block so Markdown never treats indented lines as code.
    body = " ".join(line.strip() for line in path.read_text().splitlines() if line.strip())
    return f'<figure class="diagram diagram--{name}">{body}</figure>'


def scorecard(view, data, link):
    views = {"grid": lambda: grid(data, link), "legend": lambda: legend(data), "glance": lambda: glance(data),
             "phases": lambda: phase_tables(data), "checklist": lambda: checklist(data, link),
             "beyond": lambda: beyond(data), "beyond-chips": lambda: beyond_chips(data, link),
             "frontier": lambda: frontier(data, link),
             "total": lambda: str(len(data["checkpoints"]))}
    if view.startswith("count "):
        key = view.split(" ", 1)[1]
        if key not in data["statuses"]:
            raise ContentError(f"Unknown status count: {key}")
        return str(counts(data)[key])
    if view not in views:
        raise ContentError(f"Unknown scorecard view: {view}")
    return views[view]()


INLINE = re.compile(r"<!--\s*scorecard:\s*(total|count [a-z]+)\s*-->")


def question(markdown, text):
    """Place the page question directly under the first h1."""
    lines = markdown.split("\n")
    for index, line in enumerate(lines):
        if line.startswith("# "):
            lines.insert(index + 1, f'\n<p class="page-question">{html.escape(text)}</p>')
            return "\n".join(lines)
    raise ContentError("A page with a question needs an h1")


def render(markdown, link, meta=None, data=None):
    data = data or load()
    if meta and meta.get("question"):
        markdown = question(markdown, meta["question"])
    markdown = INLINE.sub(lambda m: scorecard(m[1], data, link), markdown)

    def replace(match):
        kind, value = match[1], match[2]
        if kind == "checkpoints":
            return "\n" + chips(value, data, link) + "\n"
        if kind == "diagram":
            return "\n" + diagram(value) + "\n"
        return "\n" + scorecard(value, data, link) + "\n"
    return MARKER.sub(replace, markdown)
