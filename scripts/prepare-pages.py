#!/usr/bin/env python3
"""Prepare the archived HTTrack mirror for static hosting on GitHub Pages."""

import argparse
import os
import re
import shutil
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


URL_PATTERN = re.compile(r"(?P<url>(?:https?:)?//[^\s,\"'<>]+)", re.IGNORECASE)
WORDPRESS_SUFFIXES = (".wordpress.com", ".wordpress.org", ".wp.com")
REMOVED_ELEMENT_IDS = {
    "comments",
    "respond",
    "commentform",
    "jp-carousel-comment-form",
    "jp-carousel-comment-form-container",
}
REMOVED_ELEMENT_CLASSES = {
    "comment-list",
    "comment-navigation",
    "comment-respond",
    "comment-subscription-form",
    "comments-area",
    "comments-link",
    "jetpack-likes-widget-wrapper",
    "jetpack-subscription-modal",
    "jetpack_subscription_widget",
    "sd-like",
    "widget_blog_subscription",
    "wp-block-jetpack-subscriptions",
}


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
    content = re.sub(
        r"<script\b(?=[^>]*\bid\s*=\s*[\"']gifting-banner-js(?:-extra)?[\"'])[^>]*>.*?</script\s*>",
        "",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    content = re.sub(
        r"<link\b(?=[^>]*gifting-banner)[^>]*>",
        "",
        content,
        flags=re.IGNORECASE,
    )
    content = re.sub(r"[\"']gifting-banner[\"']\s*,?", "", content)

    def rewrite_srcset(match: re.Match) -> str:
        quote = match.group(1)
        candidates = []
        for candidate in match.group(2).split(","):
            parts = candidate.strip().split()
            if not parts:
                continue
            url = rewrite_platform_url(parts[0], page, destination)
            if url:
                candidates.append(" ".join((url, *parts[1:])))
        return f"srcset={quote}{', '.join(candidates)}{quote}" if candidates else ""

    content = re.sub(
        r"\bsrcset\s*=\s*([\"'])(.*?)\1",
        rewrite_srcset,
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
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


def remove_subscription_comment_and_like_sections(content: str) -> str:
    class SectionParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.line_starts = [0]
            self.line_starts.extend(
                match.end() for match in re.finditer("\n", content)
            )
            self.stack = []
            self.ranges = []

        def current_offset(self) -> int:
            line, column = self.getpos()
            return self.line_starts[line - 1] + column

        def should_remove(self, attrs: list[tuple[str, str | None]]) -> bool:
            attributes = dict(attrs)
            element_id = (attributes.get("id") or "").lower()
            classes = set((attributes.get("class") or "").lower().split())
            return (
                element_id in REMOVED_ELEMENT_IDS
                or element_id.startswith("like-post-wrapper-")
                or bool(classes & REMOVED_ELEMENT_CLASSES)
            )

        def handle_starttag(
            self, tag: str, attrs: list[tuple[str, str | None]]
        ) -> None:
            start = self.current_offset()
            remove = self.should_remove(attrs)
            if tag in {
                "area",
                "base",
                "br",
                "col",
                "embed",
                "hr",
                "img",
                "input",
                "link",
                "meta",
                "param",
                "source",
                "track",
                "wbr",
            }:
                if remove:
                    self.ranges.append((start, start + len(self.get_starttag_text())))
                return
            self.stack.append((tag, start, remove))

        def handle_startendtag(
            self, tag: str, attrs: list[tuple[str, str | None]]
        ) -> None:
            start = self.current_offset()
            if self.should_remove(attrs):
                self.ranges.append((start, start + len(self.get_starttag_text())))

        def handle_endtag(self, tag: str) -> None:
            index = next(
                (
                    index
                    for index in range(len(self.stack) - 1, -1, -1)
                    if self.stack[index][0] == tag
                ),
                None,
            )
            if index is None:
                return
            _, start, remove = self.stack[index]
            del self.stack[index:]
            if remove:
                end_start = self.current_offset()
                closing_tag = re.match(
                    rf"</\s*{re.escape(tag)}\s*>",
                    content[end_start:],
                    flags=re.IGNORECASE,
                )
                if closing_tag:
                    self.ranges.append((start, end_start + closing_tag.end()))

    parser = SectionParser()
    parser.feed(content)
    if not parser.ranges:
        return content

    merged_ranges = []
    for start, end in sorted(parser.ranges):
        if merged_ranges and start <= merged_ranges[-1][1]:
            merged_ranges[-1] = (merged_ranges[-1][0], max(end, merged_ranges[-1][1]))
        else:
            merged_ranges.append((start, end))
    for start, end in reversed(merged_ranges):
        content = content[:start] + content[end:]
    return content


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


def replace_favicon(content: str, page: Path, favicon: Path) -> str:
    content = re.sub(
        r"<link\b[^>]*\brel\s*=\s*([\"'])(?:shortcut\s+)?icon\1[^>]*>\s*",
        "",
        content,
        flags=re.IGNORECASE,
    )
    content = re.sub(
        r"<link\b[^>]*\brel\s*=\s*([\"'])apple-touch-icon(?:-precomposed)?\1[^>]*>\s*",
        "",
        content,
        flags=re.IGNORECASE,
    )
    content = re.sub(
        r"<meta\b[^>]*\bname\s*=\s*([\"'])msapplication-TileImage\1[^>]*>\s*",
        "",
        content,
        flags=re.IGNORECASE,
    )

    favicon_url = os.path.relpath(str(favicon), str(page.parent)).replace(os.sep, "/")
    favicon_links = (
        f'<link rel="icon" type="image/svg+xml" href="{favicon_url}" />\n'
        f'<link rel="shortcut icon" href="{favicon_url}" />'
    )
    if re.search(r"<head(?:\s[^>]*)?>", content, flags=re.IGNORECASE):
        return re.sub(
            r"(<head(?:\s[^>]*)?>)",
            rf"\1\n  {favicon_links}",
            content,
            count=1,
            flags=re.IGNORECASE,
        )
    return content


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
        ignore=shutil.ignore_patterns(
            "hts-cache", "hts-log.txt", "wp-json", "gifting-banner"
        ),
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
        updated = remove_subscription_comment_and_like_sections(updated)
        if updated != content:
            page.write_text(updated, encoding="utf-8")

    favicon_source = source.parent / "ap-monogram-parametric-sliceFavicon.svg"
    if not favicon_source.is_file():
        raise FileNotFoundError(f"Favicon asset not found: {favicon_source}")
    favicon = destination / "ap-monogram-parametric-sliceFavicon.svg"
    shutil.copy2(favicon_source, favicon)

    for page in destination.rglob("*.html"):
        content = page.read_text(encoding="utf-8", errors="replace")
        updated = replace_favicon(content, page, favicon)
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
