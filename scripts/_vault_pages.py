"""
Shared helpers for finding and reading vault pages — used by
generate_image.py and apply_image.py. Not meant to be run directly.
"""
import re
import subprocess
from pathlib import Path

import yaml

EXCLUDED_DIR_PARTS = {".obsidian", ".git"}
EXCLUDED_ROOT_FILES = {"Dashboard.md", "README.md"}
FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)


def vault_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    )
    return Path(result.stdout.strip())


def iter_pages(root: Path):
    for md_path in sorted(root.rglob("*.md")):
        rel = md_path.relative_to(root)
        if EXCLUDED_DIR_PARTS & set(rel.parts[:-1]):
            continue
        if len(rel.parts) == 1 and rel.name in EXCLUDED_ROOT_FILES:
            continue
        yield md_path, rel


def read_frontmatter(md_path: Path):
    text = md_path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        fm = None
    if not isinstance(fm, dict):
        fm = {}
    return fm, text[m.end():]


def find_page(root: Path, query: str):
    """Returns (md_path, rel_path, name, frontmatter, body) for the best
    match against a page's frontmatter `name:` (falling back to its
    filename)."""
    q = query.strip().lower()
    candidates = []
    for md_path, rel in iter_pages(root):
        fm, body = read_frontmatter(md_path)
        name = str(fm.get("name") or md_path.stem)
        candidates.append((md_path, rel, name, fm, body))

    for c in candidates:
        if c[2].strip().lower() == q:
            return c
    matches = [c for c in candidates if q in c[2].strip().lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        names = ", ".join(m[2] for m in matches[:8])
        raise SystemExit(f"'{query}' matches multiple pages: {names} — be more specific")
    raise SystemExit(f"No page found matching '{query}'")
