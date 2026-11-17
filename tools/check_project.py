"""Read-only project checks, including negative tests for chapter immutability."""

import copy
import io
import re
import unittest
import zipfile

import build_epub as build


class ProjectChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chapters = build.read_chapters()

    def test_full_chapter_plan_and_payoff_register(self):
        plan = (build.ROOT / "Continuation master plan.md").read_text(encoding="utf-8")
        outline = plan.split("## 5. Chapter architecture", 1)[1].split("## 6.", 1)[0]
        numbers = [int(n) for n in re.findall(r"(?m)^(\d+)\. \*\*", outline)]
        self.assertEqual(numbers, list(range(1, 73)))
        register = plan.split("## 6. Payoff register", 1)[1].split("## 7.", 1)[0]
        ids = re.findall(r"(?m)^\| (P\d+) \|", register)
        self.assertEqual(ids, [f"P{i:02}" for i in range(1, 26)])
        self.assertEqual(sum((62000, 68000, 66000, 70000, 70000, 67000)), 403000)

    def test_delivered_sources_match_locks(self):
        build.check_locks(self.chapters, register=False)

    def test_registration_does_not_bypass_changed_chapter(self):
        changed = copy.deepcopy(self.chapters)
        changed[0]["sha256"] = "0" * 64
        for register in (False, True):
            with self.subTest(register=register):
                with self.assertRaisesRegex(ValueError, "LOCK VIOLATION"):
                    build.check_locks(changed, register=register)

    def test_missing_locked_chapter_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Locked chapter missing"):
            build.check_locks([], register=True)

    def test_delivered_epub_matches_sources(self):
        path = build.ROOT / (
            "Mother of Learning - The Shape of After - Chapters "
            f"001-{len(self.chapters):03}.epub")
        build.validate(path.read_bytes(), self.chapters)

    def test_standalone_cover_and_embedded_cover_match(self):
        standalone = build.COVER_PATH.read_bytes()
        self.assertEqual(build.validate_cover(standalone), (1600, 2560))
        path = build.ROOT / (
            "Mother of Learning - The Shape of After - Chapters "
            f"001-{len(self.chapters):03}.epub")
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(archive.read("EPUB/cover.png"), standalone)
            opf = archive.read("EPUB/package.opf").decode("utf-8")
            self.assertIn('properties="cover-image"', opf)
            self.assertIn('id="cover-page"', opf)

    def test_epub_text_corruption_is_detected(self):
        original = build.make_archive(self.chapters)
        corrupt = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(original)) as source:
            with zipfile.ZipFile(corrupt, "w") as target:
                for info in source.infolist():
                    data = source.read(info.filename)
                    if info.filename == "EPUB/chapter-001.xhtml":
                        data = data.replace(b"<p>", b"<p>UNEXPECTED TEXT ", 1)
                    target.writestr(info, data)
        with self.assertRaisesRegex(ValueError, "Text mismatch"):
            build.validate(corrupt.getvalue(), self.chapters)


if __name__ == "__main__":
    unittest.main(verbosity=2)
