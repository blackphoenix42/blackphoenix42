#!/usr/bin/env python3
"""
Mirror all external images and snapshot non-image links from README.md

- Images/SVGs -> assets/auto/<slug>.<ext>
- Non-image links -> assets/backups/<slug>.md (title + href + timestamp)
- Records everything in assets/manifest.json and scripts/link_backups.yml

This does not rewrite the README — the monitor job does surgical swaps as needed.
"""

import os, re, json, hashlib
from datetime import datetime
from urllib.parse import urlparse
import requests, yaml
from bs4 import BeautifulSoup

README = "README.md"
ASSET_DIR = "assets/auto"
BACKUP_DIR = "assets/backups"
MANIFEST = "assets/manifest.json"
LINK_YAML = "scripts/link_backups.yml"

os.makedirs(ASSET_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LINK_YAML), exist_ok=True)

# Markdown + HTML images
IMG_MD   = re.compile(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
IMG_HTML = re.compile(r'<img\b[^>]*\bsrc=["\']([^"\']+)["\'][^>]*>', re.IGNORECASE)

# Markdown + HTML links (non-image)
LINK_MD   = re.compile(r'(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
HREF_HTML = re.compile(r'<a\b[^>]*\bhref=["\']([^"\']+)["\']', re.IGNORECASE)

SESSION = requests.Session()
TIMEOUT = 15

def is_http(u: str) -> bool:
    return u.startswith("http://") or u.startswith("https://")

def is_skip(u: str) -> bool:
    return (not is_http(u)) or u.startswith("data:") or u.startswith("#")

def sha1_8(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]

def slugify(url: str) -> str:
    host = urlparse(url).netloc.replace(":","-").replace(".","-")
    return f"{host}-{sha1_8(url)}"

def guess_img_ext(resp, url):
    ctype = resp.headers.get("content-type","").lower()
    if "svg"   in ctype: return ".svg"
    if "png"   in ctype: return ".png"
    if "jpeg"  in ctype or "jpg" in ctype: return ".jpg"
    if "gif"   in ctype: return ".gif"
    if "webp"  in ctype: return ".webp"
    # fallback: derive from path
    path = urlparse(url).path
    base = os.path.basename(path)
    if "." in base:
        ext = "." + base.split(".")[-1].lower()
        if ext in (".svg",".png",".jpg",".jpeg",".gif",".webp"): return ext
    return ".svg"

def get(url):
    try:
        r = SESSION.get(url, timeout=TIMEOUT, allow_redirects=True)
        r.raise_for_status()
        return r
    except Exception:
        return None

def page_title(html: str) -> str:
    try:
        soup = BeautifulSoup(html, "html.parser")
        t = soup.title.string if soup.title else ""
        return (t or "").strip()[:140]
    except Exception:
        return ""

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def load_yaml(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

def save_yaml(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=True)

def collect(text):
    imgs, links = set(), set()
    for _, u in IMG_MD.findall(text):
        if not is_skip(u): imgs.add(u)
    for u in IMG_HTML.findall(text):
        if not is_skip(u): imgs.add(u)
    for u in LINK_MD.findall(text):
        if not is_skip(u): links.add(u)
    for u in HREF_HTML.findall(text):
        if not is_skip(u): links.add(u)
    links -= imgs  # don't double-count images
    return list(imgs), list(links)

def sha256_bytes(b: bytes) -> str:
    import hashlib
    return hashlib.sha256(b).hexdigest()

def main():
    with open(README, "r", encoding="utf-8") as f:
        text = f.read()

    img_urls, link_urls = collect(text)
    manifest = load_json(MANIFEST, {})
    link_map = load_yaml(LINK_YAML)

    # Mirror images
    for url in img_urls:
        slug = slugify(url)
        entry = manifest.get(url, {"type":"image", "slug": slug})
        r = get(url)
        if r:
            ext = guess_img_ext(r, url)
            local = os.path.join(ASSET_DIR, f"{slug}{ext}")
            with open(local, "wb") as out:
                out.write(r.content)
            entry.update({
                "type": "image",
                "path": local.replace("\\","/"),
                "sha256": sha256_bytes(r.content),
                "bytes": len(r.content),
                "last_status": "ok",
                "last_checked": datetime.utcnow().isoformat()+"Z"
            })
        else:
            # if no previous cache, create a placeholder SVG
            local = entry.get("path")
            if not local or not os.path.exists(local):
                local = os.path.join(ASSET_DIR, f"{slug}.svg")
                if not os.path.exists(local):
                    with open(local, "w", encoding="utf-8") as out:
                        out.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="460" height="120"><rect width="100%" height="100%" fill="#0d1117"/><text x="50%" y="50%" text-anchor="middle" fill="#58A6FF" font-family="monospace" font-size="14">Unavailable: {url}</text></svg>')
            entry.update({
                "type":"image",
                "path": local.replace("\\","/"),
                "sha256": None,
                "last_status": "placeholder",
                "last_checked": datetime.utcnow().isoformat()+"Z"
            })
        manifest[url] = entry

    # Snapshot non-image links
    for url in link_urls:
        slug = slugify(url)
        entry = manifest.get(url, {"type":"link", "slug": slug})
        backup_md = os.path.join(BACKUP_DIR, f"{slug}.md")
        r = get(url)
        if r:
            title = page_title(r.text) or url
            with open(backup_md, "w", encoding="utf-8") as f:
                f.write(f"# Snapshot\n\n**Title**: {title}\n\n**Original**: <{url}>\n\n_Last refreshed: {datetime.utcnow().isoformat()}Z_\n")
            entry.update({
                "type":"link",
                "backup_path": backup_md.replace("\\","/"),
                "last_status": "ok",
                "last_checked": datetime.utcnow().isoformat()+"Z"
            })
        else:
            if not os.path.exists(backup_md):
                with open(backup_md, "w", encoding="utf-8") as f:
                    f.write(f"# Snapshot (Unavailable)\n\n**Original**: <{url}>\n\n_No content. Source unreachable at {datetime.utcnow().isoformat()}Z._\n")
            entry.update({
                "type":"link",
                "backup_path": backup_md.replace("\\","/"),
                "last_status": "down",
                "last_checked": datetime.utcnow().isoformat()+"Z"
            })
        manifest[url] = entry
        link_map[slug] = {"primary": url, "backup": entry["backup_path"]}

    save_json(MANIFEST, manifest)
    save_yaml(LINK_YAML, link_map)
    print(f"Mirrored {len(img_urls)} images; snapshotted {len(link_urls)} links.")

if __name__ == "__main__":
    main()