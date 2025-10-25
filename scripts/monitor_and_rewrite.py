#!/usr/bin/env python3
"""
Every 30 minutes:
- Validate all image/link URLs (manifest + README)
- IMAGES: swap external <-> local asset in README based on health; refresh backups when origin recovers
- LINKS : swap primary <-> backup (assets/backups/*.md) based on health; refresh snapshot when origin recovers
- MARKERS: auto-disable/enable ANY dynamic block markers when block-internal links are broken/healthy
  Supported marker styles:
    <!-- NAME_START --> ... <!-- NAME_END -->
    <!-- NAME:START --> ... <!-- NAME:END -->
  Disabled forms:
    <!-- NAME_START_DISABLED --> / <!-- NAME_END_DISABLED -->
    <!-- NAME:START_DISABLED --> / <!-- NAME:END_DISABLED -->
- Writes readme_health_report.md
"""

import os, re, json
from datetime import datetime
import requests, yaml

README   = "README.md"
MANIFEST = "assets/manifest.json"
LINK_YML = "scripts/link_backups.yml"
REPORT   = "readme_health_report.md"

# Markdown + HTML images and links
IMG_MD   = re.compile(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
IMG_HTML = re.compile(r'<img\b[^>]*\bsrc=["\']([^"\']+)["\'][^>]*>', re.IGNORECASE)
LINK_MD  = re.compile(r'(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
HREF_HTML= re.compile(r'<a\b[^>]*\bhref=["\']([^"\']+)["\']', re.IGNORECASE)

# Marker patterns
# Style A: <!-- NAME_START --> ... <!-- NAME_END -->
MARKER_A_START = re.compile(r'<!--\s*([A-Z0-9:_-]+)_START\s*-->', re.IGNORECASE)
MARKER_A_END   = re.compile(r'<!--\s*([A-Z0-9:_-]+)_END\s*-->',   re.IGNORECASE)
# Style B: <!-- NAME:START --> ... <!-- NAME:END -->
MARKER_B_START = re.compile(r'<!--\s*([A-Z0-9:_-]+):START\s*-->', re.IGNORECASE)
MARKER_B_END   = re.compile(r'<!--\s*([A-Z0-9:_-]+):END\s*-->',   re.IGNORECASE)

# Disabled variants
def disabled_a(name): return f"<!-- {name}_START_DISABLED -->", f"<!-- {name}_END_DISABLED -->"
def active_a(name):    return f"<!-- {name}_START -->",          f"<!-- {name}_END -->"
def disabled_b(name): return f"<!-- {name}:START_DISABLED -->",  f"<!-- {name}:END_DISABLED -->"
def active_b(name):    return f"<!-- {name}:START -->",           f"<!-- {name}:END -->"

SESSION = requests.Session()
TIMEOUT = 12

def http_ok(url: str) -> bool:
    if not (url.startswith("http://") or url.startswith("https://")):
        return False
    try:
        r = SESSION.head(url, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code >= 400 or r.status_code == 405:
            r = SESSION.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True)
        return r.status_code < 400
    except Exception:
        return False

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def load_yaml(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

def write(path, s):
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)

def collect_readme_urls(text):
    imgs, links = set(), set()
    for _, u in IMG_MD.findall(text):   imgs.add(u)
    for u in IMG_HTML.findall(text):    imgs.add(u)
    for u in LINK_MD.findall(text):     links.add(u)
    for u in HREF_HTML.findall(text):   links.add(u)
    return list(imgs), list(links)

def swap_url(text: str, old: str, new: str) -> str:
    # Replace only inside Markdown/HTML contexts to avoid accidental edits.
    text = re.sub(rf'(!\[[^\]]*\]\()({re.escape(old)})(\))', rf'\1{new}\3', text)
    text = re.sub(rf'(<img\b[^>]*\bsrc=["\'])({re.escape(old)})(["\'])', rf'\1{new}\3', text, flags=re.IGNORECASE)
    text = re.sub(rf'(?<!\!)\[[^\]]*\]\(({re.escape(old)})\)', lambda m: m.group(0).replace(old, new), text)
    text = re.sub(rf'(<a\b[^>]*\bhref=["\'])({re.escape(old)})(["\'])', rf'\1{new}\3', text, flags=re.IGNORECASE)
    return text

def find_blocks(text: str):
    """
    Find all marker blocks for both styles, including disabled ones.
    Returns list of dicts: {name, style, start_idx, end_idx, start_str, end_str, disabled}
    """
    blocks = []
    # Helper to index all markers by name & positions
    def pair_style(start_re, end_re, style, to_active, to_disabled):
        starts = [(m.group(1), m.start(), m.end()) for m in start_re.finditer(text)]
        ends   = [(m.group(1), m.start(), m.end()) for m in end_re.finditer(text)]
        # also catch disabled forms
        starts_dis = [(m.group(1), m.start(), m.end()) for m in re.finditer(start_re.pattern.replace("START", "START_DISABLED"), text, re.IGNORECASE)]
        ends_dis   = [(m.group(1), m.start(), m.end()) for m in re.finditer(end_re.pattern.replace("END", "END_DISABLED"),   text, re.IGNORECASE)]

        # active pairs
        for name, s0, s1 in starts:
            # find the first matching END for same name after s1
            e_match = next(((n, e0, e1) for (n, e0, e1) in ends if n.lower()==name.lower() and e0 > s1), None)
            if e_match:
                _, e0, e1 = e_match
                blocks.append({
                    "name": name, "style": style, "disabled": False,
                    "start_idx": s0, "end_idx": e1,
                    "start_str": to_active(name)[0], "end_str": to_active(name)[1]
                })
        # disabled pairs
        for name, s0, s1 in starts_dis:
            e_match = next(((n, e0, e1) for (n, e0, e1) in ends_dis if n.lower()==name.lower() and e0 > s1), None)
            if e_match:
                _, e0, e1 = e_match
                blocks.append({
                    "name": name, "style": style, "disabled": True,
                    "start_idx": s0, "end_idx": e1,
                    "start_str": to_disabled(name)[0], "end_str": to_disabled(name)[1]
                })

    pair_style(MARKER_A_START, MARKER_A_END, "underscore", active_a, disabled_a)
    pair_style(MARKER_B_START, MARKER_B_END, "colon",      active_b, disabled_b)
    # sort by order in doc
    blocks.sort(key=lambda b: b["start_idx"])
    return blocks

def urls_in_text(s: str):
    imgs, links = set(), set()
    for _, u in IMG_MD.findall(s): imgs.add(u)
    for u in IMG_HTML.findall(s): imgs.add(u)
    for u in LINK_MD.findall(s):  links.add(u)
    for u in HREF_HTML.findall(s):links.add(u)
    return list(imgs), list(links)

def toggle_block(text: str, block: dict, enable: bool) -> str:
    name = block["name"]
    if block["style"] == "underscore":
        a_start, a_end = active_a(name)
        d_start, d_end = disabled_a(name)
    else:
        a_start, a_end = active_b(name)
        d_start, d_end = disabled_b(name)

    if enable:
        # disabled -> active
        text = text.replace(d_start, a_start).replace(d_end, a_end)
    else:
        # active -> disabled
        text = text.replace(a_start, d_start).replace(a_end, d_end)
    return text

def refresh_image_backup(origin_url: str, manifest: dict):
    """If origin recovered, refresh local mirror so backup stays new."""
    meta = manifest.get(origin_url)
    if not meta or meta.get("type") != "image":
        return
    path = meta.get("path")
    if not path:
        return
    try:
        r = SESSION.get(origin_url, timeout=10, allow_redirects=True)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)
        meta["last_status"] = "ok"
        meta["last_checked"] = datetime.utcnow().isoformat()+"Z"
        manifest[origin_url] = meta
    except Exception:
        pass

def refresh_link_backup(primary: str, link_map: dict):
    """If link recovered, refresh its backup snapshot file."""
    # find slug mapping that has this primary
    for slug, m in link_map.items():
        if m.get("primary") == primary:
            backup = m.get("backup")
            if not backup:
                return
            try:
                r = SESSION.get(primary, timeout=10, allow_redirects=True)
                r.raise_for_status()
                title = primary
                # Very tiny parse: try to fetch <title>
                m = re.search(r"<title[^>]*>(.*?)</title>", r.text, flags=re.IGNORECASE|re.DOTALL)
                if m:
                    title = re.sub(r"\s+", " ", m.group(1).strip())[:140]
                with open(backup, "w", encoding="utf-8") as f:
                    f.write(f"# Snapshot\n\n**Title**: {title}\n\n**Original**: <{primary}>\n\n_Last refreshed: {datetime.utcnow().isoformat()}Z_\n")
            except Exception:
                pass
            return

def main():
    manifest = load_json(MANIFEST)
    link_map = load_yaml(LINK_YML)

    with open(README, "r", encoding="utf-8") as f:
        text = f.read()

    orig_text = text
    broken, fixed = [], []

    # 1) Image fallbacks / restores
    readme_imgs, _ = collect_readme_urls(text)
    for url in readme_imgs:
        is_external = url.startswith("http://") or url.startswith("https://")
        if is_external:
            if not http_ok(url):
                meta = manifest.get(url, {})
                local = meta.get("path")
                if local and os.path.exists(local):
                    text = swap_url(text, url, local)
                    broken.append(url)
        else:
            # local path; find its origin
            origin = None
            for k, v in manifest.items():
                if v.get("type") == "image" and v.get("path") == url:
                    origin = k; break
            if origin and http_ok(origin):
                text = swap_url(text, url, origin)
                fixed.append(origin)
                refresh_image_backup(origin, manifest)

    # 2) Link fallbacks / restores
    _, readme_links = collect_readme_urls(text)
    # create a primary->backup map quickly
    p2b = {m["primary"]: m["backup"] for m in link_map.values() if m.get("primary") and m.get("backup")}
    b2p = {m["backup"]: m["primary"] for m in link_map.values() if m.get("primary") and m.get("backup")}

    # swap to backup when down
    for primary, backup in p2b.items():
        if primary in text and not http_ok(primary):
            text = swap_url(text, primary, backup)
            broken.append(primary)
    # restore to primary when healthy
    for backup, primary in b2p.items():
        if backup in text and http_ok(primary):
            text = swap_url(text, backup, primary)
            fixed.append(primary)
            refresh_link_backup(primary, link_map)

    # 3) Block marker gating (generalized)
    blocks = find_blocks(text)
    # evaluate block health
    for blk in blocks:
        segment = text[blk["start_idx"]:blk["end_idx"]]
        imgs_b, links_b = urls_in_text(segment)
        unhealthy = any(http_ok(u) is False for u in (imgs_b + links_b) if u.startswith("http"))
        if not blk["disabled"] and unhealthy:
            text = toggle_block(text, blk, enable=False)
            broken.append(f"block:{blk['name']}")
        elif blk["disabled"] and not unhealthy:
            text = toggle_block(text, blk, enable=True)
            fixed.append(f"block:{blk['name']}")

    # 4) Save README if changed; persist manifest (if image refreshes happened)
    if text != orig_text:
        with open(README, "w", encoding="utf-8") as f:
            f.write(text)
    # manifest may have been refreshed by image backups
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # 5) Health report
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        f"# README Health Report\n\n**Generated**: {now}\n",
        "## Summary",
        f"- Broken handled this run: {len(broken)}",
        f"- Restored this run: {len(fixed)}",
        ""
    ]
    if broken:
        lines.append("## ❌ Broken / Switched\n")
        lines += [f"- {u}" for u in broken]
        lines.append("")
    if fixed:
        lines.append("## ✅ Restored to Primary\n")
        lines += [f"- {u}" for u in fixed]
        lines.append("")
    write(REPORT, "\n".join(lines))
    print("Monitor rewrite done.")

if __name__ == "__main__":
    main()