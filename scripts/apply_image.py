#!/usr/bin/env python3
"""
Land a chosen image candidate (from generate_image.py) in this vault:
copies it into Images/ and sets it as the page's `image:` frontmatter
property.

Does not touch git at all — review with `git status` / `git diff` and
commit it yourself, same as any other vault edit. Once committed and
pushed, re-run theflat.gen.nz's fetch-swn-data.sh to pull the change in
(it goes through the same resize/recompress/thumbnail pipeline as every
other synced image).

Usage:
  scripts/apply_image.py "Governor Lian Osk" .image-candidates/governor-lian-osk/2.png
  scripts/apply_image.py "Governor Lian Osk" ./chosen.png --filename lianosk-v2.png
"""
import argparse
import re
import shutil
from pathlib import Path

from _vault_pages import FRONTMATTER_RE, find_page, vault_root

# NOTE: no \s* here — \s matches newlines, and a greedy \s* after "image:"
# on a line with an empty value (just "image:" then a bare newline) would
# swallow the newline and keep matching into the *next* line, silently
# deleting whatever key follows (caught this against a real page: it ate
# a `tags:` line). `.*` alone already covers same-line whitespace/content.
IMAGE_LINE_RE = re.compile(r"^image:.*$", re.MULTILINE)


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def read_preserving_newline(path: Path):
    """Python's text-mode read/write normalizes all line endings to \\n,
    which would silently rewrite the entire file for any vault page saved
    with CRLF (this vault mixes both — some Compendium files imported
    from elsewhere use CRLF, most are LF). Detect it and normalize to \\n
    ourselves only for processing, so it can be converted back before
    writing and only the actually-changed line shows up in git diff."""
    raw = path.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in raw else "\n"
    return raw.replace("\r\n", "\n"), newline


def write_preserving_newline(path: Path, text: str, newline: str) -> None:
    if newline == "\r\n":
        text = text.replace("\n", "\r\n")
    path.write_bytes(text.encode("utf-8"))


def set_image_field(md_text: str, image_rel_path: str) -> str:
    m = FRONTMATTER_RE.match(md_text)
    if not m:
        raise SystemExit("Page file has no YAML frontmatter block — can't set `image:` safely")
    fm_block = m.group(1)
    line = f"image: {image_rel_path}"
    if IMAGE_LINE_RE.search(fm_block):
        new_fm = IMAGE_LINE_RE.sub(line, fm_block, count=1)
    else:
        new_fm = fm_block.rstrip("\n") + "\n" + line
    return md_text[:m.start(1)] + new_fm + md_text[m.end(1):]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page", help="Page name (matches frontmatter `name:`, falling back to the filename)")
    ap.add_argument("image", help="Path to the chosen candidate image file")
    ap.add_argument("--filename", help="Output filename under Images/ (default: slugified page name)")
    args = ap.parse_args()

    chosen = Path(args.image).resolve()
    if not chosen.is_file():
        raise SystemExit(f"Not a file: {chosen}")

    root = vault_root()
    md_path, rel, name, fm, body = find_page(root, args.page)
    slug = slugify(name)
    filename = args.filename or (slug + chosen.suffix.lower())

    images_dir = root / "Images"
    images_dir.mkdir(exist_ok=True)
    dest = images_dir / filename
    if dest.exists() and dest.resolve() != chosen:
        raise SystemExit(f"Images/{filename} already exists — pass --filename to pick a different name")
    shutil.copyfile(chosen, dest)

    md_text, newline = read_preserving_newline(md_path)
    write_preserving_newline(md_path, set_image_field(md_text, f"Images/{filename}"), newline)

    print(f"Wrote Images/{filename}")
    print(f"Updated image: field in {rel}")
    print("\nNothing committed — review with `git status` / `git diff` and commit when you're happy.")


if __name__ == "__main__":
    main()
