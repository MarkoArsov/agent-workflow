#!/usr/bin/env python3
"""Check a built site, including anchors and assets under a project subpath."""
from __future__ import annotations
import argparse
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

class Page(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.ids, self.links = set(), []
        self.feed(content)
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "a" and attrs.get("name"):
            self.ids.add(attrs["name"])
        for key in ("href", "src"):
            if attrs.get(key):
                self.links.append(attrs[key])

def check(root, prefix="/agent-workflow/"):
    root = Path(root).resolve()
    pages = {p: Page(p.read_text()) for p in root.rglob("*.html")}
    failures, count = [], 0
    for path, page in pages.items():
        for link in page.links:
            url = urlsplit(link)
            if url.scheme or url.netloc or not url.path and not url.fragment:
                continue
            name = unquote(url.path)
            if name.startswith("/"):
                if not name.startswith(prefix):
                    failures.append(f"{path.relative_to(root)}: URL escapes project prefix: {link}")
                    continue
                target = root / name[len(prefix):]
            else:
                target = path.parent / name if name else path
            target = target.resolve()
            if target.is_dir():
                target /= "index.html"
            count += 1
            if not target.is_relative_to(root) or not target.is_file():
                failures.append(f"{path.relative_to(root)}: missing target {link}")
            elif url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                failures.append(f"{path.relative_to(root)}: missing anchor {link}")
    for path in root.rglob("*.css"):
        for asset in re.findall(r"url\(['\"]?([^)'\"\s]+)", path.read_text()):
            if urlsplit(asset).scheme or asset.startswith("#"):
                continue
            target = (path.parent / unquote(urlsplit(asset).path)).resolve()
            count += 1
            if not target.is_file():
                failures.append(f"{path.relative_to(root)}: missing CSS asset {asset}")
    return count, failures

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    parser.add_argument("--prefix", default="/agent-workflow/")
    args = parser.parse_args()
    count, failures = check(args.site, args.prefix)
    for failure in failures:
        print(failure)
    print(f"Checked {count} internal links/assets; {len(failures)} failures.")
    raise SystemExit(bool(failures))
