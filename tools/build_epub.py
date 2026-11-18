"""Build the cumulative EPUB and verify it against immutable chapter sources.

Chapter format: one '# Chapter N: Title' heading, plain prose paragraphs,
and '* * *' scene separators. Unsupported Markdown is rejected, not dropped.
First delivery of reviewed new chapters: python tools/build_epub.py --register-new
Subsequent builds: python tools/build_epub.py
"""

import argparse
import hashlib
import html
import io
import json
import posixpath
import re
import shutil
import struct
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TITLE = "The Shape of After"
BOOK_ID = "urn:uuid:a5b16564-e182-48b1-ad6f-4b0287a18c1e"
XHTML = "http://www.w3.org/1999/xhtml"
OPF = "http://www.idpf.org/2007/opf"
EPUB = "http://www.idpf.org/2007/ops"
NCX = "http://www.daisy.org/z3986/2005/ncx/"
XML_DECL = '<?xml version="1.0" encoding="utf-8"?>\n'
COVER_PATH = ROOT / "The Shape of After - Cover.png"
COVER_HREF = "cover.png"


def validate_cover(data):
    require(data.startswith(b"\x89PNG\r\n\x1a\n"), "Cover is not a PNG image")
    require(len(data) >= 24, "Truncated cover PNG")
    width, height = struct.unpack(">II", data[16:24])
    require(width >= 1000 and height >= 1500, "Cover resolution is too low")
    require(0.5 <= width / height <= 0.85, "Cover aspect ratio is unsuitable for a book")
    return width, height


def require(condition, message):
    if not condition:
        raise ValueError(message)


def word_count(text):
    return len(re.findall(r"\b\w+(?:['’\-]\w+)*\b", text))


def page(title, body):
    return (XML_DECL + f'<html xmlns="{XHTML}" xmlns:epub="{EPUB}" '
            'xml:lang="en" lang="en"><head>'
            f'<title>{html.escape(title)}</title>'
            '<link rel="stylesheet" type="text/css" href="style.css"/>'
            f'</head><body>{body}</body></html>')


def read_chapters():
    chapters = []
    for path in sorted((ROOT / "chapters").glob("*.md")):
        match = re.fullmatch(r"Chapter (\d{3}) - (.+)\.md", path.name)
        require(match is not None, f"Invalid chapter filename: {path.name}")
        number, title = int(match[1]), match[2]
        raw = path.read_bytes()
        text = raw.decode("utf-8").replace("\r\n", "\n").strip()
        blocks = re.split(r"\n\s*\n", text)
        heading = f"Chapter {number}: {title}"
        require(blocks[0] == "# " + heading, f"Heading mismatch: {path.name}")
        paragraphs, body = [], [f'<h1 id="chapter-{number:03}">{html.escape(heading)}</h1>']
        scenes = 0
        for block in blocks[1:]:
            if block == "* * *":
                scenes += 1
                body.append('<hr class="scene-break" aria-label="Scene break"/>')
                continue
            require(not re.search(r"(?m)^(#|>|```|[-+]\s|\d+\.\s)", block),
                    f"Unsupported block Markdown in {path.name}")
            require(not re.search(r"\*|`|!\[|\]\(", block),
                    f"Unsupported inline Markdown in {path.name}")
            paragraph = " ".join(block.splitlines())
            require("\ufffd" not in paragraph, f"Replacement character in {path.name}")
            paragraphs.append(paragraph)
            body.append(f"<p>{html.escape(paragraph)}</p>")
        require(paragraphs, f"Empty chapter: {path.name}")
        chapters.append({
            "path": path.relative_to(ROOT).as_posix(), "number": number,
            "title": title, "heading": heading,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "words": word_count(" ".join(paragraphs)),
            "paragraphs": paragraphs, "scene_breaks": scenes,
            "href": f"chapter-{number:03}.xhtml",
            "xhtml": page(heading, "\n".join(body)),
        })
    require(chapters, "No completed chapters found")
    require([c["number"] for c in chapters] == list(range(1, len(chapters) + 1)),
            "Chapters must be consecutive, starting at 001")
    return chapters


def check_locks(chapters, register):
    path = ROOT / "chapter-locks.json"
    locks = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
        "format": 1, "policy": "No changes to delivered chapters without user permission.",
        "chapters": {},
    }
    current = {c["path"]: c for c in chapters}
    for name, record in locks["chapters"].items():
        require(name in current, f"Locked chapter missing: {name}")
        require(record["sha256"] == current[name]["sha256"],
                f"LOCK VIOLATION: {name}. User authorization required before revision.")
    for name, chapter in current.items():
        if name not in locks["chapters"]:
            require(register, f"Unregistered chapter: {name}. Review before --register-new.")
            locks["chapters"][name] = {
                "sha256": chapter["sha256"], "narrative_words": chapter["words"],
                "registered_utc": datetime.now(timezone.utc).isoformat(),
            }
    return path, locks


def make_archive(chapters):
    count = len(chapters)
    cover_data = COVER_PATH.read_bytes()
    validate_cover(cover_data)
    modified = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    contents = '<nav epub:type="toc" id="toc"><h1>Contents</h1><ol>'
    contents += '<li><a href="cover.xhtml">Cover</a></li>'
    contents += '<li><a href="title.xhtml">Title and edition</a></li>'
    contents += "".join(f'<li><a href="{c["href"]}">{html.escape(c["heading"])}</a></li>'
                        for c in chapters)
    contents += '</ol></nav><nav epub:type="landmarks" hidden="hidden"><ol>'
    contents += '<li><a epub:type="cover" href="cover.xhtml">Cover</a></li>'
    contents += '<li><a epub:type="bodymatter" href="chapter-001.xhtml">Start reading</a></li>'
    contents += '</ol></nav>'
    title = ('<section epub:type="titlepage"><h1>The Shape of After</h1>'
             '<p class="subtitle">An unofficial continuation of Mother of Learning</p>'
             f'<p>Reading edition: Chapters 001–{count:03}</p>'
             '<p>Original world and characters created by Domagoj Kurmaic (nobody103).</p>'
             '<p>This continuation is AI-assisted fan fiction developed at the reader’s '
             'direction. It is not written or endorsed by the original author.</p>'
             '<p>This edition contains only completed continuation chapters. '
             'The full story is ongoing.</p></section>')
    manifest = ''.join(f'<item id="c{c["number"]:03}" href="{c["href"]}" '
                       'media-type="application/xhtml+xml"/>' for c in chapters)
    spine = ''.join(f'<itemref idref="c{c["number"]:03}"/>' for c in chapters)
    package = (XML_DECL + f'<package xmlns="{OPF}" version="3.0" unique-identifier="bookid">'
               '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
               f'<dc:identifier id="bookid">{BOOK_ID}</dc:identifier>'
               f'<dc:title>{TITLE}</dc:title><dc:language>en</dc:language>'
               '<dc:creator>AI-assisted fan continuation</dc:creator>'
               '<dc:description>An unofficial continuation of Mother of Learning.</dc:description>'
               f'<meta property="dcterms:modified">{modified}</meta></metadata>'
               '<manifest><item id="cover-page" href="cover.xhtml" media-type="application/xhtml+xml"/>'
               '<item id="cover-image" href="cover.png" media-type="image/png" properties="cover-image"/>'
               '<item id="title" href="title.xhtml" media-type="application/xhtml+xml"/>'
               '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
               '<item id="css" href="style.css" media-type="text/css"/>'
               '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
               f'{manifest}</manifest><spine toc="ncx"><itemref idref="cover-page"/>'
               '<itemref idref="title"/>'
               f'<itemref idref="nav" linear="no"/>{spine}</spine></package>')
    points = ''.join(
        f'<navPoint id="n{c["number"]}" playOrder="{c["number"]}"><navLabel>'
        f'<text>{html.escape(c["heading"])}</text></navLabel>'
        f'<content src="{c["href"]}"/></navPoint>' for c in chapters)
    ncx = (XML_DECL + f'<ncx xmlns="{NCX}" version="2005-1"><head>'
           f'<meta name="dtb:uid" content="{BOOK_ID}"/>'
           '<meta name="dtb:depth" content="1"/><meta name="dtb:totalPageCount" content="0"/>'
           '<meta name="dtb:maxPageNumber" content="0"/></head>'
           f'<docTitle><text>{TITLE}</text></docTitle><navMap>{points}</navMap></ncx>')
    files = {
        "META-INF/container.xml": XML_DECL +
        '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">'
        '<rootfiles><rootfile full-path="EPUB/package.opf" '
        'media-type="application/oebps-package+xml"/></rootfiles></container>',
        "EPUB/package.opf": package, "EPUB/nav.xhtml": page("Contents", contents),
        "EPUB/cover.xhtml": page("Cover", '<section epub:type="cover"><img src="cover.png" '
                                            'alt="The Shape of After — a moonlit city before a great '
                                            'broken clock dial"/></section>'),
        "EPUB/title.xhtml": page(TITLE, title), "EPUB/toc.ncx": ncx,
        "EPUB/style.css": ('body { margin: 5%; line-height: 1.5; } '
                           'h1 { text-align: center; margin: 1.5em 0; } '
                           'p { margin: 0; text-indent: 1.2em; } '
                           'h1 + p, hr + p { text-indent: 0; } '
                           'section p { text-align: center; text-indent: 0; margin: 1em 0; } '
                           '.scene-break { width: 20%; margin: 1.8em auto; } '
                           'nav li { margin: 0.6em 0; }'),
    }
    files["EPUB/cover.png"] = cover_data
    files.update({"EPUB/" + c["href"]: c["xhtml"] for c in chapters})
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        for name, content in files.items():
            archive.writestr(name, content if isinstance(content, bytes) else content.encode("utf-8"))
    return buffer.getvalue()


def validate(data, chapters):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        require(archive.testzip() is None, "ZIP integrity failure")
        entries = archive.infolist()
        require(entries[0].filename == "mimetype" and entries[0].compress_type == 0,
                "EPUB mimetype must be first and uncompressed")
        require(archive.read("mimetype") == b"application/epub+zip", "Wrong mimetype")
        names = set(archive.namelist())
        require(len(names) == len(entries), "Duplicate archive paths")
        trees = {}
        for name in names:
            if name.endswith((".xml", ".opf", ".xhtml", ".ncx")):
                trees[name] = ET.fromstring(archive.read(name))
        container = trees["META-INF/container.xml"]
        rootfile = container.find(".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile")
        require(rootfile is not None and rootfile.attrib["full-path"] == "EPUB/package.opf",
                "Invalid container rootfile")
        opf = trees["EPUB/package.opf"]
        items = opf.findall(f"{{{OPF}}}manifest/{{{OPF}}}item")
        manifest = {item.attrib["id"]: item.attrib for item in items}
        require(len(manifest) == len(items), "Duplicate manifest IDs")
        require(manifest.get("cover-image", {}).get("properties") == "cover-image"
                and manifest["cover-image"].get("media-type") == "image/png"
                and manifest["cover-image"].get("href") == COVER_HREF,
                "Cover image is not identified in the OPF manifest")
        width, height = validate_cover(archive.read("EPUB/cover.png"))
        require(f"EPUB/{COVER_HREF}" in names and "EPUB/cover.xhtml" in names,
                "Cover resources missing")
        require({"EPUB/" + item["href"] for item in manifest.values()} ==
                {name for name in names if name.startswith("EPUB/") and name != "EPUB/package.opf"},
                "Manifest does not match archive resources")
        refs = [node.attrib["idref"] for node in opf.findall(f"{{{OPF}}}spine/{{{OPF}}}itemref")]
        require(refs == ["cover-page", "title", "nav"] + [f'c{c["number"]:03}' for c in chapters],
                "Wrong spine order")
        for name, tree in trees.items():
            for element in tree.iter():
                for attribute in ("href", "src"):
                    link = element.get(attribute)
                    if link is not None:
                        target = posixpath.normpath(posixpath.join(posixpath.dirname(name), link.split("#")[0]))
                        require(target in names, f"Broken link: {name} -> {link}")
        nav = trees["EPUB/nav.xhtml"]
        toc = next(n for n in nav.iter(f"{{{XHTML}}}nav") if n.get(f"{{{EPUB}}}type") == "toc")
        links = [a.get("href") for a in toc.iter(f"{{{XHTML}}}a")]
        require(links == ["cover.xhtml", "title.xhtml"] + [c["href"] for c in chapters],
                "Wrong navigation order")
        for chapter in chapters:
            tree = trees["EPUB/" + chapter["href"]]
            paragraphs = ["".join(p.itertext()) for p in tree.iter(f"{{{XHTML}}}p")]
            require(paragraphs == chapter["paragraphs"], f'Text mismatch: {chapter["path"]}')
            require(len(list(tree.iter(f"{{{XHTML}}}hr"))) == chapter["scene_breaks"],
                    "Scene separator mismatch")
            require(next(tree.iter(f"{{{XHTML}}}h1")).text == chapter["heading"], "Heading mismatch")


def atomic_write(path, data):
    require(path.parent.is_dir(), f"Missing parent directory: {path.parent}")
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as stream:
        temp = Path(stream.name)
        stream.write(data)
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register-new", action="store_true")
    parser.add_argument("--inspect", action="store_true", help="Check source format and count words without writing")
    args = parser.parse_args()
    chapters = read_chapters()
    if args.inspect:
        print(json.dumps([{k: c[k] for k in ("path", "words", "scene_breaks", "sha256")}
                          for c in chapters], indent=2))
        return
    require(COVER_PATH.is_file(), f"Missing standalone cover image: {COVER_PATH.name}")
    cover_width, cover_height = validate_cover(COVER_PATH.read_bytes())
    lock_path, locks = check_locks(chapters, args.register_new)
    data = make_archive(chapters)
    validate(data, chapters)
    output = ROOT / f"Mother of Learning - The Shape of After - Chapters 001-{len(chapters):03}.epub"
    atomic_write(output, data)
    validate(output.read_bytes(), chapters)
    epubcheck = shutil.which("epubcheck")
    external = "not available; built-in structural and source-text checks passed"
    if epubcheck:
        subprocess.run([epubcheck, str(output)], check=True)
        external = "passed"
    # Recheck sources before registering their delivery hashes.
    for chapter in chapters:
        require(hashlib.sha256((ROOT / chapter["path"]).read_bytes()).hexdigest() == chapter["sha256"],
                "Chapter changed while building")
    atomic_write(lock_path, (json.dumps(locks, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    report = {
        "epub": output.name, "chapter_count": len(chapters),
        "narrative_words": sum(c["words"] for c in chapters),
        "epub_sha256": hashlib.sha256(data).hexdigest(), "epubcheck": external,
        "cover": {"path": COVER_PATH.name, "width": cover_width,
                  "height": cover_height, "embedded": True},
        "checks": ["ZIP integrity", "EPUB packaging", "cover image and OPF designation",
                   "cover page and rendering resource", "XML parsing", "manifest resources",
                   "spine and navigation order", "internal links", "source paragraph equality",
                   "scene separators", "locked source hashes"],
        "device_rendering": "not tested",
        "chapters": [{k: c[k] for k in ("path", "number", "title", "words", "sha256", "scene_breaks")}
                     for c in chapters],
    }
    atomic_write(ROOT / "epub-build-report.json",
                 (json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
