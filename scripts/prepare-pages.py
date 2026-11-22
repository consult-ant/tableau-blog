#!/usr/bin/env python3
"""Prepare the archived HTTrack mirror for static hosting on GitHub Pages."""

import argparse
import re
import shutil
from pathlib import Path


def bundle_extension(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    sample = re.sub(r"/\*.*?\*/", " ", text[:8192], flags=re.DOTALL).lstrip()

    if re.match(
        r"(?:\(\s*\(\s*\)\s*=>|\(\s*function\b|!function\b|"
        r"(?:var|let|const)\s+|(?:document|window)\.)",
        sample,
    ):
        return ".js"
    if re.match(r"(?:@|[.#:*]|[a-zA-Z][\w-]*\s*(?:\{|,))", sample):
        return ".css"

    raise ValueError(f"Unable to identify CSS or JavaScript bundle: {path}")


def prepare_site(source: Path, destination: Path) -> None:
    source = source.resolve()
    destination = destination.resolve()
    if not (source / "consult-ant.uk" / "_static").is_dir():
        raise FileNotFoundError(f"Not an archived blog directory: {source}")
    if destination == source or source in destination.parents:
        raise ValueError("The deploy directory must be outside the source archive")
    if destination.exists():
        raise FileExistsError(f"Deploy directory already exists: {destination}")

    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("hts-cache", "hts-log.txt"),
    )

    static_dir = destination / "consult-ant.uk" / "_static"
    extensions = {}
    for bundle in static_dir.glob("*.html"):
        extension = bundle_extension(bundle)
        renamed = bundle.with_suffix(extension)
        bundle.rename(renamed)
        extensions[bundle.stem] = extension

    if not extensions:
        raise ValueError(f"No static bundles found in {static_dir}")

    def replace_bundle(match: re.Match) -> str:
        name = match.group(1)
        if name not in extensions:
            raise ValueError(f"Referenced static bundle was not found: {name}")
        return f"_static/{name}{extensions[name]}"

    for page in destination.rglob("*.html"):
        content = page.read_text(encoding="utf-8", errors="replace")
        updated = re.sub(r"_static/(index[a-z0-9]+)\.html", replace_bundle, content)
        if updated != content:
            page.write_text(updated, encoding="utf-8")

    for backend_file in destination.rglob("*.php"):
        backend_file.unlink()

    (destination / ".nojekyll").touch()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="HTTrack archive directory")
    parser.add_argument("destination", type=Path, help="New deploy directory")
    args = parser.parse_args()
    prepare_site(args.source, args.destination)


if __name__ == "__main__":
    main()
