#!/usr/bin/env python3
"""Prepare the archived HTTrack mirror for static hosting on GitHub Pages."""

import argparse
import os
import re
import shutil
from pathlib import Path
from urllib.parse import unquote, urlsplit


URL_PATTERN = re.compile(r"(?P<url>(?:https?:)?//[^\s\"'<>]+)", re.IGNORECASE)
WORDPRESS_SUFFIXES = (".wordpress.com", ".wordpress.org", ".wp.com")


def local_file(root: Path, url_path: str) -> Path | None:
    candidate = (root / unquote(url_path).lstrip("/")).resolve()
    if candidate != root and root not in candidate.parents:
        return None
    if candidate.is_file():
        return candidate
    if candidate.is_dir() and (candidate / "index.html").is_file():
        return candidate / "index.html"
    if not candidate.suffix and (candidate.with_suffix(".html")).is_file():
        return candidate.with_suffix(".html")
    return None


def rewrite_platform_url(url: str, page: Path, destination: Path) -> str:
    parsed = urlsplit(f"https:{url}" if url.startswith("//") else url)
    host = (parsed.hostname or "").lower()

    if host == "consultant94152356.wordpress.com":
        target = destination / "consult-ant.uk" / "index.html"
    elif host == "consult-ant.uk":
        target = local_file(destination / "consult-ant.uk", parsed.path)
    elif (
        host.endswith(WORDPRESS_SUFFIXES)
        or host in {"wordpress.com", "wordpress.org", "wp.me"}
    ):
        if host == "stats.wp.com" or (
            host == "s0.wp.com" and parsed.path.startswith("/wp-content/js/bilmur")
        ):
            return ""
        target = local_file(destination / host, parsed.path)
    else:
        return url

    if target is None or not target.is_file():
        return ""
    relative = os.path.relpath(str(target), str(page.parent)).replace(os.sep, "/")
    return f"{relative}#{parsed.fragment}" if parsed.fragment else relative


def clean_platform_references(content: str, page: Path, destination: Path) -> str:
    content = URL_PATTERN.sub(
        lambda match: rewrite_platform_url(match.group("url"), page, destination),
        content,
    )
    content = re.sub(
        r"<(script|iframe|form)\b[^>]*>.*?</\1\s*>",
        lambda match: (
            ""
            if re.search(
                r"\b(?:src|action)\s*=\s*([\"'])\s*\1",
                match.group(0).split(">", 1)[0],
                re.IGNORECASE,
            )
            else match.group(0)
        ),
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    content = re.sub(
        r"<img\b(?=[^>]*\bsrc\s*=\s*([\"'])\s*\1)[^>]*>",
        "",
        content,
        flags=re.IGNORECASE,
    )
    content = re.sub(
        r"\s+\b(?:href|src|action|data-[\w:-]+|content|poster|cite|formaction)\s*=\s*([\"'])\s*\1",
        "",
        content,
        flags=re.IGNORECASE,
    )
    content = re.sub(
        r"<link\b[^>]*\bhref\s*=\s*([\"'])\s*\1[^>]*>",
        "",
        content,
        flags=re.IGNORECASE,
    )
    content = re.sub(
        r"<link\b[^>]*(?:wp-json|xmlrpc(?:0db0)?\.php|rel\s*=\s*([\"'])shortlink\1)[^>]*>",
        "",
        content,
        flags=re.IGNORECASE,
    )
    content = re.sub(
        r"<!--\s*(?:Mirrored from|Added by HTTrack)[\s\S]*?-->",
        "",
        content,
        flags=re.IGNORECASE,
    )
    content = re.sub(
        r"<meta\b(?=[^>]*\bname\s*=\s*([\"'])generator\1)[^>]*>",
        "",
        content,
        flags=re.IGNORECASE,
    )
    content = re.sub(
        r"<a\b[^>]*>\s*(?:WordPress\.com|Proudly powered by WordPress)\s*</a>",
        "",
        content,
        flags=re.IGNORECASE,
    )
    content = re.sub(r"\s*Theme:\s*Karuna\.?", "", content, flags=re.IGNORECASE)
    return re.sub(r"\bWordPress(?:\.com|\.org)?\b", "", content, flags=re.IGNORECASE)


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
        ignore=shutil.ignore_patterns("hts-cache", "hts-log.txt", "wp-json"),
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
        updated = clean_platform_references(updated, page, destination)
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
