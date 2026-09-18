"""Behavioral checks for the small documentation validator."""
import importlib.util
from contextlib import chdir
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_repository.py"
SPEC = importlib.util.spec_from_file_location("repository_checks", MODULE_PATH)
CHECKS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKS)


class MarkdownLinkTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.doc = self.root / "docs" / "guide.md"
        self.doc.parent.mkdir()

    def write_doc(self, content):
        self.doc.write_text(content, encoding="utf-8")

    def test_relative_unicode_and_encoded_space_paths(self):
        (self.root / "中文 Guide.md").write_text("# Guide\n", encoding="utf-8")
        self.write_doc("[Guide](../中文%20Guide.md#guide)\n")
        self.assertEqual(CHECKS.check_links(self.doc, self.root), [])

    def test_external_fragment_and_code_examples_are_not_local_files(self):
        self.write_doc(
            "[Web](https://example.com/page) [Mail](mailto:example@example.com) [Here](#here)\n"
            "```markdown\n[example](missing.md)\n```\n"
            "Inline example: `[example](also-missing.md)`\n"
        )
        self.assertEqual(CHECKS.check_links(self.doc, self.root), [])

    def test_missing_relative_and_reference_targets_fail(self):
        self.write_doc("[Missing](missing.md)\n[reference]: absent.md\n")
        errors = CHECKS.check_links(self.doc, self.root)
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("missing.md" in error for error in errors))

    def test_outside_repository_target_is_rejected(self):
        self.write_doc("[Outside](../../outside.md)\n")
        errors = CHECKS.check_links(self.doc, self.root)
        self.assertEqual(len(errors), 1)
        self.assertIn("outside repository", errors[0])

    def test_invalid_utf8_is_reported(self):
        self.doc.write_bytes(b"\xff\xfe\x00")
        errors = CHECKS.check_links(self.doc, self.root)
        self.assertEqual(len(errors), 1)
        self.assertIn("UTF-8", errors[0])

    def test_relative_document_path_is_normalized(self):
        self.write_doc("# Guide\n")
        with chdir(self.root):
            self.assertEqual(CHECKS.check_links(Path("docs/guide.md"), self.root), [])

    def test_document_outside_root_is_reported_without_reading(self):
        outside = self.root.parent / "not-in-this-repository.md"
        errors = CHECKS.check_links(outside, self.root)
        self.assertEqual(len(errors), 1)
        self.assertIn("outside repository", errors[0])

    def test_security_contact_uses_current_repository(self):
        config = Path(__file__).resolve().parents[1] / ".github" / "ISSUE_TEMPLATE" / "config.yml"
        text = config.read_text(encoding="utf-8")
        self.assertIn(
            "https://github.com/fws94/product9-token-saver/security/advisories/new",
            text,
        )


if __name__ == "__main__":
    unittest.main()
