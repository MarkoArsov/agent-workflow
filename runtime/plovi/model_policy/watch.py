"""Optional benchmark evidence. Never evaluates routes or stores credentials."""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.request
from .core import route_key, validate_route
from .storage import read, write

SOURCE = "https://artificialanalysis.ai/api/v2/language/models/free"
ATTRIBUTION = "https://artificialanalysis.ai/"
MAX_BYTES = 1_500_000
MAX_PAGES = 8
TOTAL_SECONDS = 45
INDICES = tuple("artificial_analysis_" + name + "_index" for name in (
    "intelligence", "coding", "agentic", "finance_and_accounting", "strategy_and_ops",
    "legal", "healthcare_and_medical", "engineering", "economics"))
PRICES = ("price_1m_input_tokens", "price_1m_output_tokens")
PERFORMANCE = ("median_output_tokens_per_second", "median_time_to_first_token_seconds",
               "median_time_to_first_answer_token_seconds", "median_end_to_end_response_time_seconds")


def load_key(key_file=None):
    value = os.environ.get("AA_API_KEY", "").strip()
    if not value and key_file is not None:
        try:
            path = Path(key_file)
            if path.stat().st_size > 65_536:
                raise ValueError("Selected key file exceeds size limit")
            for line in path.read_text(encoding="utf-8").splitlines():
                match = re.fullmatch(r"\s*(?:export\s+)?AA_API_KEY\s*=\s*(.*?)\s*", line)
                if match:
                    value = match[1]
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                        value = value[1:-1]
                    break
        except (OSError, UnicodeError):
            raise ValueError("Cannot read selected AA key file") from None
    if not value:
        raise ValueError("Set AA_API_KEY or select --key-file; previous evidence was preserved")
    if len(value) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in value):
        raise ValueError("Invalid AA key format")
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if fp is not None:
            fp.close()
        raise ValueError("Artificial Analysis redirect refused; previous evidence was preserved")


def _number(value, *, nonnegative=True):
    if value is not None and (type(value) not in (float, int) or not math.isfinite(value) or (nonnegative and value < 0)):
        raise ValueError("Invalid benchmark number")
    return value


def _text(value):
    if not isinstance(value, str) or not 0 < len(value) <= 300 or not value.isprintable():
        raise ValueError("Invalid benchmark identity")
    return value


def normalize(rows):
    models, seen = [], set()
    for item in rows:
        if not isinstance(item, dict):
            raise ValueError("Invalid benchmark model")
        slug = _text(item.get("slug"))
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,199}", slug) or slug in seen:
            raise ValueError("Invalid or duplicate benchmark slug")
        seen.add(slug)
        creator = item.get("model_creator")
        if not isinstance(creator, dict):
            raise ValueError("Invalid benchmark creator")
        released = item.get("release_date")
        if released is not None:
            if not isinstance(released, str) or date.fromisoformat(released).isoformat() != released:
                raise ValueError("Invalid release date")
        model = {"id": _text(item.get("id")), "slug": slug, "name": _text(item.get("name")),
                 "release_date": released, "creator": _text(creator.get("name")),
                 "creator_id": _text(creator.get("id"))}
        for field, keys in (("evaluations", INDICES), ("pricing", PRICES), ("performance", PERFORMANCE)):
            values = item.get(field)
            if not isinstance(values, dict):
                raise ValueError("Missing benchmark metrics object")
            model[field] = {key: _number(values.get(key), nonnegative=field != "evaluations") for key in keys}
        models.append(model)
    return sorted(models, key=lambda row: row["slug"])


def fetch_models(key):
    opener = urllib.request.build_opener(NoRedirect())
    deadline, used = time.monotonic() + TOTAL_SECONDS, 0
    rows, version, tier, total = [], None, None, None
    for page in range(1, MAX_PAGES + 1):
        request = urllib.request.Request(f"{SOURCE}?page={page}", headers={
            "x-api-key": key, "Accept": "application/json", "User-Agent": "plovi-model-watch"})
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError("Artificial Analysis request exceeded time limit")
        try:
            with opener.open(request, timeout=min(10, remaining)) as response:
                chunks = []
                while True:
                    chunk = response.read1(min(65_536, MAX_BYTES - used + 1))
                    used += len(chunk)
                    if used > MAX_BYTES or time.monotonic() > deadline:
                        raise ValueError("Artificial Analysis response exceeded size/time limit")
                    if not chunk:
                        break
                    chunks.append(chunk)
                payload = json.loads(b"".join(chunks))
        except urllib.error.HTTPError as exc:
            exc.close()
            raise ValueError(f"Artificial Analysis HTTP {exc.code}; previous evidence was preserved") from None
        except (OSError, urllib.error.URLError, UnicodeError, json.JSONDecodeError):
            raise ValueError("Artificial Analysis fetch failed; check access/network; previous evidence was preserved") from None
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ValueError("Invalid Artificial Analysis response")
        pagination = payload.get("pagination")
        if not isinstance(pagination, dict):
            raise ValueError("Missing Artificial Analysis pagination")
        pages = pagination.get("total_pages")
        if (type(pagination.get("page")) is not int or pagination["page"] != page
                or type(pages) is not int or not page <= pages <= MAX_PAGES
                or type(pagination.get("has_more")) is not bool
                or pagination["has_more"] != (page < pages)):
            raise ValueError("Invalid or excessive Artificial Analysis pagination")
        observed_version = _number(payload.get("intelligence_index_version"))
        observed_tier = payload.get("tier")
        if observed_version is None or not isinstance(observed_tier, str) or observed_tier not in {"free", "pro", "commercial"}:
            raise ValueError("Invalid Artificial Analysis version/tier")
        if page > 1 and (pages, observed_version, observed_tier) != (total, version, tier):
            raise ValueError("Artificial Analysis pages changed during fetch")
        total, version, tier = pages, observed_version, observed_tier
        rows.extend(payload["data"])
        if not pagination["has_more"]:
            try:
                models = normalize(rows)
            except (ValueError, TypeError, OverflowError):
                raise ValueError("Invalid benchmark model data; previous evidence was preserved") from None
            return models, version, tier
    raise ValueError("Artificial Analysis pagination exceeds limit")


def summarize(previous, current, aliases, catalogue, routes, registry, today):
    old = {r["slug"]: r for r in previous.get("models", [])}
    new = {r["slug"]: r for r in current["models"]}
    baseline = not previous
    version_changed = bool(previous) and previous.get("intelligence_index_version") != current["intelligence_index_version"]
    mappings = {}
    if not isinstance(aliases, dict) or aliases.get("schema_version") != 1 or not isinstance(aliases.get("routes"), list):
        raise ValueError("Invalid benchmark alias table")
    for alias in aliases["routes"]:
        if not isinstance(alias, dict):
            raise ValueError("Invalid benchmark alias")
        validate_route({k: alias[k] for k in ("provider", "model") if k in alias})
        key = route_key(alias)
        if key in mappings or not isinstance(alias.get("slug"), str):
            raise ValueError("Invalid or duplicate benchmark alias")
        mappings[key] = alias["slug"]
    entries = {}
    for row in registry:
        key = route_key(row)
        entries[key] = {**row, "lineage": row.get("lineage", entries.get(key, {}).get("lineage"))}
    labs = {entries.get(route_key(chain[0]), {}).get("lineage") for chain in routes.values() if chain}
    labs.discard(None)
    def relevant(row):
        creator = re.sub(r"[^a-z0-9]", "", row["creator"].lower())
        names = {"spacexai": "xai"}
        return names.get(creator, creator) in labs
    route_rows = []
    for stage, chain in sorted(routes.items()):
        if not chain:
            continue
        route = chain[0]
        host = catalogue.get("providers", {}).get(route["provider"], {})
        observed = next((m for m in host.get("models", []) if m.get("model") == route["model"]), None)
        try:
            stamp = datetime.fromisoformat(host.get("observed_at", ""))
            fresh = stamp.tzinfo is not None and 0 <= (today - stamp.astimezone(timezone.utc).date()).days <= 30
        except (TypeError, ValueError):
            fresh = False
        status = ("missing-catalogue" if not host else "stale-catalogue" if not fresh or host.get("refresh_failed") else
                  "unavailable" if host.get("installed") is False or (observed and observed.get("status") == "unavailable") else
                  "missing-id" if observed is None else observed.get("status", "unknown"))
        slug = mappings.get(route_key(route))
        route_rows.append({"stage": stage, **route, "slug": slug, "matched": slug in new if slug else False,
                           "catalogue_status": status,
                           "evidence": new.get(slug) if slug else None})
    cutoff = today - timedelta(days=45)
    def listing(slugs, index):
        return [index[slug] for slug in sorted(slugs) if relevant(index[slug])]
    changed = [] if baseline or version_changed else listing({s for s in new.keys() & old.keys() if new[s] != old[s]}, new)
    return {"source": SOURCE, "attribution": ATTRIBUTION, "fetched_at": current["fetched_at"],
            "baseline": baseline, "index_version_changed": version_changed,
            "intelligence_index_version": current["intelligence_index_version"],
            "new": [] if baseline else listing(new.keys() - old.keys(), new),
            "removed": [] if baseline else listing(old.keys() - new.keys(), old), "changed": changed,
            "recent": [r for r in new.values() if relevant(r) and r["release_date"] is not None
                       and cutoff <= date.fromisoformat(r["release_date"]) <= today],
            "routes": route_rows, "model_count": len(new), "focus_lineages": sorted(labs)}


def refresh(store, key_file=None, *, now=None):
    key = load_key(key_file)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Watch time must include a timezone")
    with store.lock():
        effective = store.effective()
        models, version, tier = fetch_models(key)
        current = {"schema_version": 1, "source": SOURCE, "attribution": ATTRIBUTION,
                   "fetched_at": now.astimezone(timezone.utc).isoformat(), "tier": tier,
                   "intelligence_index_version": version, "models": models}
        routes = dict(effective.get("defaults", {}))
        routes.update(effective.get("pins", {}))
        default = routes.pop("default", None)
        if default is not None:
            for stage in ("specify", "implement-tests", "implement", "review"):
                routes.setdefault(stage, default)
        path = store.data / "watch.json"
        report = summarize(read(path, {}), current, read(Path(__file__).with_name("aliases.json")),
                           read(store.data / "catalogue.json", {}), routes,
                           read(Path(__file__).with_name("registry.json")) + effective.get("registry", []),
                           now.astimezone(timezone.utc).date())
        serialized = json.dumps({"snapshot": current, "report": report})
        if key in serialized or len((json.dumps(current, indent=2, sort_keys=True) + "\n").encode()) > 2_000_000:
            raise ValueError("Benchmark evidence failed safety/size validation; previous evidence was preserved")
        write(path, current)
    return {**report, "path": str(path), "routes_changed": False}
