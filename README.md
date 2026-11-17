# Mother of Learning — *The Shape of After*

An unofficial, AI-assisted continuation of Domagoj Kurmaic's (nobody103) serial novel
*Mother of Learning*, written at the reader's own request.

**There is deliberately no synopsis in this file.** What the story is about, and what
happens in it, is not summarised anywhere in this repository's public-facing files —
the story only exists as prose inside the EPUB and the chapter sources. If you are
reading, read the book, not the docs.

## Reading

- **Current edition:** `Mother of Learning - The Shape of After - Chapters 001-002.epub`
  — one cumulative, reader-ready EPUB containing every chapter delivered so far
  (2 chapters, 12,238 words of prose, plus a title page that states the fan status).
- **Cover:** `The Shape of After - Cover.png` (1600 × 2560), embedded as the EPUB cover.
- Opens in any standard EPUB reader (Calibre, Kobo, Apple Books, Moon+, Thorium).
- The edition is rebuilt from scratch whenever a chapter is added, so the file name
  always says `001-NNN` and covers all chapters ever delivered.

## Repository layout

| Path | What it is |
| --- | --- |
| `chapters/` | One Markdown file per chapter — the only source of story text |
| `Mother of Learning - The Shape of After - Chapters 001-NNN.epub` | The cumulative reading edition, generated from `chapters/` |
| `The Shape of After - Cover.png` | Cover art, embedded in the EPUB |
| `tools/build_epub.py` | Builds *and* validates the EPUB |
| `tools/check_project.py` | Read-only project checks, including immutability tests |
| `tools/render_cover.py`, `tools/extract_source.py` | Helper scripts for cover art and local source reference |
| `chapter-locks.json` | Hash locks for every delivered chapter |
| `epub-build-report.json` | Report from the last build: counts, hashes, checks |
| `AGENTS.md` | Working rules for the AI assistant in this repository (spoiler-free by design) |
| `Sequel concept.md`, `Continuation master plan.md`, `Continuity log.md`, `Master plan review.md` | Author-side working notes and planning documents. Not reading material, and not summarised here. |

## Building

```
python tools/build_epub.py                 # rebuild the cumulative edition from all chapters
python tools/build_epub.py --inspect       # validate sources and count words, write nothing
python tools/build_epub.py --register-new  # after review, lock newly written chapters once
python tools/check_project.py              # run the repository's own checks
```

A build only produces an EPUB if every check passes: ZIP integrity, EPUB 3 packaging,
cover designation, XML parsing, manifest/spine/navigation order, internal links,
paragraph-by-paragraph equality with the Markdown sources, scene separators, and the
locked chapter hashes. The result is validated twice: in memory and again from disk.

## Project rules

- **Delivered chapters are immutable.** Their SHA-256 hashes live in `chapter-locks.json`;
  editing a delivered chapter fails the build with `LOCK VIOLATION` until the reader
  explicitly authorises a revision.
- **Chapter format:** one `# Chapter N: Title` heading, plain prose paragraphs, and
  `* * *` scene separators. Any other Markdown is rejected rather than silently dropped.
- **Numbering:** chapters must be consecutive starting at `001`, and the generated EPUB
  always contains all of them.
- **No spoilers.** Chat replies, commit messages, reports and documentation never reveal
  what happens in the story. See `AGENTS.md`.

## Fan work

The world, characters and original story belong to Domagoj Kurmaic (nobody103). This is
an unofficial, non-commercial fan continuation and is not written or endorsed by the
original author. The original novel's EPUB and any text extracted from it are excluded
by `.gitignore` and stay on the local machine as reference only.
