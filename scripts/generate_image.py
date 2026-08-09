#!/usr/bin/env python3
"""
Generate candidate portrait/scene images for a vault page via the xAI
Grok Imagine API, and lay them out in a local contact sheet for review.

Only calls the (paid) xAI API and writes local scratch files under
.image-candidates/ (gitignored) — never touches git. Once you've picked
a candidate, hand it to apply_image.py to land it in this vault. The
theflat.gen.nz site picks up the change (resized, recompressed, with a
thumbnail generated) the next time its own sync script runs.

Usage:
  XAI_API_KEY=xai-... scripts/generate_image.py "Governor Lian Osk"
  scripts/generate_image.py "Governor Lian Osk" --prompt "custom prompt text"
  scripts/generate_image.py "Governor Lian Osk" --dry-run

Requires the XAI_API_KEY environment variable, or a KEY=value line for
it in a .env file at the vault root (gitignored) — get a key from
https://console.x.ai. That's a separate developer account from the
consumer Grok Imagine app/grok.com login. xAI's public docs did not
list per-image pricing or rate limits, so check the console before
generating in bulk. Requires PyYAML (`pip install pyyaml`).
"""
import argparse
import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from _vault_pages import vault_root, find_page

API_URL = "https://api.x.ai/v1/images/generations"
MODEL = "grok-imagine-image-quality"


def load_api_key(root: Path):
    key = os.environ.get("XAI_API_KEY")
    if key:
        return key
    env_file = root / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("XAI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def draft_prompt(name: str, fm: dict, body: str) -> str:
    """Compose a starting prompt from the page's own frontmatter and body
    text, so there's usually something reasonable to send without having
    to write a description from scratch. Always printed before use —
    pass --prompt to override it outright."""
    bits = []
    if fm.get("type"):
        bits.append(str(fm["type"]))
    if fm.get("role"):
        bits.append(str(fm["role"]))
    tags = fm.get("tags") or []
    if tags:
        bits.append(", ".join(str(t) for t in tags))

    section = None
    m = re.search(r"##\s*Appearance.*?\n(.*?)(?:\n##|\Z)", body, re.S | re.I)
    if not m:
        m = re.search(r"##\s*Overview\n(.*?)(?:\n##|\Z)", body, re.S | re.I)
    if m:
        section = " ".join(m.group(1).split())[:400]

    parts = [name]
    if bits:
        parts.append("(" + "; ".join(bits) + ")")
    if section:
        parts.append("— " + section)
    parts.append(
        "Cinematic sci-fi portrait, moody frontier lighting, gritty "
        "photorealistic detail, consistent with a Stars Without Number "
        "campaign's existing character art."
    )
    return " ".join(parts)


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def request_images(prompt: str, n: int, aspect_ratio: str, resolution: str, api_key: str) -> dict:
    body = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "n": n,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "response_format": "url",
    }).encode("utf-8")
    req = urllib.request.Request(
        API_URL, data=body, method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"xAI API error {exc.code}: {detail}")


def download(url: str, dest_stem: Path) -> Path:
    req = urllib.request.Request(url, headers={"User-Agent": "swn-image-gen/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        content_type = resp.headers.get("Content-Type", "image/png").split(";")[0]
        ext = mimetypes.guess_extension(content_type) or ".png"
        data = resp.read()
    out = dest_stem.with_suffix(ext)
    out.write_bytes(data)
    return out


def write_contact_sheet(out_dir: Path, page_name: str, files: list) -> None:
    items = "\n".join(
        f'<figure><img src="{f.name}" alt="candidate {i + 1}">'
        f'<figcaption>#{i + 1} — {f.name}</figcaption></figure>'
        for i, f in enumerate(files)
    )
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Candidates for {page_name}</title>
<style>
body {{ background:#111; color:#eee; font-family:system-ui,sans-serif; padding:24px; }}
h1 {{ font-size:1.1rem; }}
p {{ color:#8ab4f8; font-family:ui-monospace,monospace; font-size:0.85rem; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:16px; }}
figure {{ margin:0; background:#1a1a1a; border:1px solid #333; border-radius:10px; overflow:hidden; }}
img {{ width:100%; display:block; }}
figcaption {{ padding:8px; font-size:0.8rem; color:#ccc; text-align:center; }}
</style></head><body>
<h1>Candidates for {page_name}</h1>
<p>scripts/apply_image.py "{page_name}" {out_dir}/&lt;N&gt;.ext</p>
<div class="grid">{items}</div>
</body></html>"""
    (out_dir / "index.html").write_text(html, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page", help="Page name (matches frontmatter `name:`, falling back to the filename)")
    ap.add_argument("--prompt", help="Exact prompt to use instead of drafting one from the page")
    ap.add_argument("--n", type=int, default=4, help="Number of candidates (default 4)")
    ap.add_argument("--aspect-ratio", default="2:3", help='Default "2:3", matching existing portraits')
    ap.add_argument("--resolution", default="2k", choices=["1k", "2k"])
    ap.add_argument("--out", help="Output directory (default: .image-candidates/<slug>/)")
    ap.add_argument("--dry-run", action="store_true", help="Print the prompt/request and exit — no API call, no cost")
    args = ap.parse_args()

    root = vault_root()
    md_path, rel, name, fm, body = find_page(root, args.page)
    prompt = args.prompt or draft_prompt(name, fm, body)
    slug = slugify(name)
    out_dir = Path(args.out) if args.out else root / ".image-candidates" / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Page:   {name}  ({rel})")
    print(f"Prompt: {prompt}")
    print(f"n={args.n}  aspect_ratio={args.aspect_ratio}  resolution={args.resolution}")

    if args.dry_run:
        print("\n--dry-run: not calling the API.")
        return

    api_key = load_api_key(root)
    if not api_key:
        raise SystemExit(
            "XAI_API_KEY is not set (checked the environment and .env). Get a key "
            "from https://console.x.ai — a separate developer account from the "
            "consumer Grok Imagine app — then either export it or add "
            "XAI_API_KEY=... to a .env file at the vault root (already gitignored)."
        )

    result = request_images(prompt, args.n, args.aspect_ratio, args.resolution, api_key)
    images = result.get("data", [])
    if not images:
        raise SystemExit(f"No images in response: {result}")

    files = []
    for i, item in enumerate(images):
        url = item.get("url")
        if not url:
            print(f"warning: candidate {i + 1} has no url ({item})", file=sys.stderr)
            continue
        dest = download(url, out_dir / str(i + 1))
        files.append(dest)
        print(f"  saved candidate {i + 1}: {dest}")

    if not files:
        raise SystemExit("No candidates downloaded successfully.")

    write_contact_sheet(out_dir, name, files)
    print(f"\nReview: {out_dir / 'index.html'}")
    print(f'Then:   scripts/apply_image.py "{name}" {out_dir}/<N>.<ext>')


if __name__ == "__main__":
    main()
