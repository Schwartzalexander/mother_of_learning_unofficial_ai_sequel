# Steering rules for AI assistants in this repository

Read this before doing anything here. These rules persist across sessions.

## 1. Never spoil the reader (highest priority)

The reader is following this story as it is written and does **not** want to know what
happens in it. Never reveal, paraphrase, hint at, or ask-leading-about story content —
not in chat replies, and not in commit messages, READMEs, reports, plans, logs, tests,
file names, or code comments.

Treat all of these as spoilers and do not produce them:

- events inside any chapter, past or planned; endings, twists, reveals, who lives, who dies
- summaries or "recaps" of delivered chapters or of the planning documents
- previews, teasers, "what's next", cliffhanger descriptions, foreshadowing explanations
- thematic or character "analysis" that exposes story outcomes
- confirming or denying anything the reader guesses about the plot
- quoting or pasting text from the original novel (it is also copyrighted material)

The correct response to "what happens in chapter 3?" / "summarise my plan file" is a
**metadata-only** answer: chapter number, title, word count, scene-break count, file
path, hash, build status. Say plainly that you do not discuss story content, and offer
the metadata or the file itself. Only an explicit, in-the-moment instruction from this
same reader overrides this rule — and then only for exactly what was asked.

**Do write the chapters anyway.** The rule is about *talking about* the story, never
about writing it. Produce prose into `chapters/Chapter NNN - Title.md` as asked, and
report the result neutrally (number, word count, hash, EPUB rebuilt, checks passed).

## 2. Chapter sources are immutable once delivered

- Every delivered chapter's SHA-256 lives in `chapter-locks.json`.
- A modified delivered chapter fails the build with `LOCK VIOLATION`.
- Never edit, rewrite, reformat or "improve" a delivered chapter without the reader's
  explicit permission first. New chapters are locked with
  `python tools/build_epub.py --register-new` only after the reader has received them.

## 3. Chapter and build mechanics

- Chapter format: one `# Chapter N: Title` heading, plain prose paragraphs, `* * *`
  scene separators. Any other Markdown is rejected by the builder, not silently dropped.
- Chapters must be consecutive from `001`. Keep titles spoiler-light too.
- Build the cumulative edition with `python tools/build_epub.py`; it always contains
  every chapter delivered so far and is named `... Chapters 001-NNN.epub`.
- Verify with `python tools/check_project.py` (7 checks; all must pass, `OK`).
- `Domagoj Kurmaic - Mother of Learning.epub` and `.scratch/` are git-ignored: local
  reference material for the original novel, never commit or redistribute it.

## 4. Commit and push hygiene

Commit messages describe tooling, formatting, counts, and file operations — never story
content. A commit touching `chapters/` may say only that a chapter number was added.
