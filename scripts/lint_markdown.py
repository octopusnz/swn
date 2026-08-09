#!/usr/bin/env python3
"""
Lint (and optionally fix) the vault's Markdown files with rumdl.

Reads the shared .markdownlint.json at the vault root, which is also
picked up by the VS Code markdownlint extension — so the IDE's inline
warnings and this script always agree.

Usage:
    scripts/lint_markdown.py            # check campaign content (default)
    scripts/lint_markdown.py --fix      # check and auto-fix campaign content
    scripts/lint_markdown.py --all      # check the whole vault, incl. Compendium
    scripts/lint_markdown.py --all --fix
"""
import argparse
import subprocess
import sys

from _vault_pages import vault_root

CAMPAIGN_DIRS = [
    "Sectors", "Systems", "Worlds", "NPCs", "Ships", "Vehicles",
    "Factions", "z_templates",
]
ALL_DIRS = CAMPAIGN_DIRS + ["Compendium"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="include Compendium/ (default: campaign content only)")
    parser.add_argument("--fix", action="store_true", help="auto-fix issues where possible")
    args = parser.parse_args()

    root = vault_root()
    dirs = ALL_DIRS if args.all else CAMPAIGN_DIRS
    paths = [str(root / d) for d in dirs if (root / d).is_dir()]

    cmd = ["rumdl", "check", *paths]
    if args.fix:
        cmd.append("--fix")

    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
