"""Extract plain text from the supplied original novel EPUB for continuity checks.

Read-only with respect to the EPUB. Writes plain text under .scratch/.
Usage: python tools/extract_source.py [--limit N]   (N = spine documents from the end)
"""

import argparse
import html
import html.parser
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "Domagoj Kurmaic - Mother of Learning.epub"
SCRATCH = ROOT / ".scratch"
CONTAINER_NS = "{urn:oasis:names:tc:opendocument:xmlns:container}"
OPF = "http://www.idpf.org/2007/opf"
XHTML = "http://www.w3.org/1999/xhtml"


class TextExtractor(html.parser.HTMLParser):
    BLOCK = {"p", "div", "br", "h1", "h2", "h3", "h4", "li", "tr", "blockquote"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        elif tag in self.BLOCK:
            self.parts.append("\n\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def spine_hrefs(archive):
    container = ET.fromstring(archive.read("META-INF/container.xml"))
    rootfile = container.find(f".//{CONTAINER_NS}rootfile")
    opf_path = rootfile.attrib["full-path"]
    base = posixpath.dirname(opf_path)
    opf = ET.fromstring(archive.read(opf_path))
    manifest = {item.get("id"): item.get("href")
                for item in opf.findall(f"{{{OPF}}}manifest/{{{OPF}}}item")}
    refs = [ref.get("idref") for ref in opf.findall(f"{{{OPF}}}spine/{{{OPF}}}itemref")]
    paths = []
    for ref in refs:
        href = manifest.get(ref)
        if not href:
            continue
        full = posixpath.normpath(posixpath.join(base, href)) if base else href
        paths.append(full)
    return paths


def to_text(raw):
    text = raw.decode("utf-8", "replace")
    text = re.sub(r"<(html|body)[^>]*>", "\n", text, flags=re.I | re.S)
    text = re.sub(r"(?i)^\s*<\?xml[^>]*\?>", "", text)
    text = re.sub(r"(?i)<!DOCTYPE[^>]*>", "", text)
    parser = TextExtractor()
    parser.feed(text)
    joined = "".join(parser.parts)
    joined = joined.replace("\u00a0", " ")
    joined = re.sub(r"[ \t]+", " ", joined)
    joined = re.sub(r"\n{3,}", "\n\n", joined)
    return "\n".join(line.strip() for line in joined.split("\n")).strip()


def main():
    parser = argparse.ArgumentParser(description=__name__)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--start", type=int, default=0, help="spine offset from the start")
    args = parser.parse_args()
    SCRATCH.mkdir(exist_ok=True)
    with zipfile.ZipFile(SOURCE) as archive:
        hrefs = spine_hrefs(archive)
        names = set(archive.namelist())
        picked = hrefs[args.start:] if args.start else hrefs[-args.limit:]
        out = []
        for href in picked:
            name = href if href in names else (href[len("./"):] if href.startswith("./") else None)
            if name is None:
                continue
            title_match = re.search(r"split_(\d+)", name)
            marker = f"===== spine item {title_match.group(1) if title_match else name} ====="
            out.append(marker + "\n" + to_text(archive.read(name)))
        path = SCRATCH / ("source_tail.txt" if not args.start else "source_slice.txt")
        path.write_text("\n\n".join(out), encoding="utf-8")
    print(f"{len(picked)} documents, {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
