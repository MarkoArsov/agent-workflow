#!/usr/bin/env python3
"""Copy and check documentation assets derived from the canonical design tokens."""
from pathlib import Path
import argparse
import json
ROOT = Path(__file__).resolve().parents[1]

def expected():
    design = json.loads((ROOT / "design/tokens.json").read_text())
    styles = [style for group in design["type"]["groups"] for style in group["styles"]]
    text = (ROOT / "design/tokens.css").read_text().replace('url("fonts/', 'url("../fonts/')
    text += '\n/* Source: design/tokens.json. Type variables are derived from its existing styles. */\n:root {\n'
    for style in styles:
        for field, suffix in (("fontSize", "size"), ("lineHeight", "line"), ("fontWeight", "weight"), ("letterSpacing", "tracking")):
            if field in style:
                text += f'  --type-{style["name"]}-{suffix}: {style[field]};\n'
    text += '}\n'
    result = {"docs/assets/css/tokens.css": text.encode()}
    for name in ("Geist-Variable.woff2", "GeistMono-Variable.woff2"):
        result["docs/assets/fonts/" + name] = (ROOT / "design/fonts" / name).read_bytes()
    result["docs/assets/fonts/license.txt"] = (ROOT / "design/fonts/OFL.txt").read_bytes()
    for target, source in {"logo.svg":"plovi-lockup-light.svg", "logo-light.svg":"plovi-lockup-dark.svg", "mark.svg":"plovi-mark-light.svg", "mark-light.svg":"plovi-mark-dark.svg", "favicon.svg":"plovi-app-icon.svg", "og.svg":"plovi-social-card.svg", "apple-touch-icon.svg":"plovi-app-icon.svg"}.items():
        result["docs/assets/brand/" + target] = (ROOT / "design/brand" / source).read_bytes()
    colors = {item["name"]: item["value"] for item in design["color"]["tokens"]}
    for theme in ("dark", "light"):
        value = {"theme":"base", "themeVariables": {"darkMode":theme == "dark", "fontFamily":"Geist", "primaryColor":colors["surface-raised"][theme], "primaryTextColor":colors["ink"][theme], "primaryBorderColor":colors["border-strong"][theme], "lineColor":colors["ink-subtle"][theme], "background":colors["bg"][theme]}}
        result[f"docs-data/diagrams/theme-{theme}.json"] = (json.dumps(value, indent=2) + '\n').encode()
    return result


def generate(check=False):
    stale = []
    for relative, data in expected().items():
        path = ROOT / relative
        if not path.exists() or path.read_bytes() != data:
            stale.append(relative)
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
    if check and stale:
        raise SystemExit('Stale design assets: ' + ', '.join(stale))
    print('Documentation design assets are current.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--check', action='store_true')
    generate(parser.parse_args().check)
