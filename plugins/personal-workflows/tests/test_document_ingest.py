import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from zipfile import ZipFile


PLUGIN = Path(__file__).resolve().parents[1]
SCRIPT = PLUGIN / "skills" / "doc-ingest" / "scripts" / "document_ingest.py"

SPEC = importlib.util.spec_from_file_location("personal_document_ingest", SCRIPT)
document_ingest = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(document_ingest)


def write_promotable_fresh(path, manifest="new evidence"):
    path.mkdir()
    (path / "manifest.md").write_text(manifest, encoding="utf-8")
    normalized = path / "sources" / "S1" / "content.md"
    normalized.parent.mkdir(parents=True)
    normalized.write_text("# Brief\n\nEvidence.\n", encoding="utf-8")
    report = {
        "status": "COMPLETE",
        "source_root": str((path.parent / "source").resolve()),
        "output_root": str(path.resolve()),
        "sources": [
            {
                "id": "S1",
                "path": "brief.txt",
                "format": "txt",
                "status": "COMPLETE",
                "coverage": "COMPLETE",
                "method": "direct text read",
                "normalized": "sources/S1/content.md",
                "assets": [],
                "visuals": [],
                "warnings": [],
            }
        ],
    }
    (path / "extraction-report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )


class DocumentIngestTest(unittest.TestCase):
    def test_plain_text_normalization_is_complete(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            output = root / "evidence"
            source.mkdir()
            original = b"Alpha requirement.\n"
            (source / "brief.txt").write_bytes(original)

            report = document_ingest.normalize(source, output)

            self.assertEqual(report["status"], "COMPLETE")
            self.assertEqual(len(report["sources"]), 1)
            item = report["sources"][0]
            self.assertEqual(item["id"], "S1")
            self.assertEqual(item["path"], "brief.txt")
            self.assertEqual(item["status"], "COMPLETE")
            self.assertEqual(item["coverage"], "COMPLETE")
            self.assertEqual(item["normalized"], "sources/S1/content.md")
            self.assertEqual(item["warnings"], [])
            self.assertTrue((output / item["normalized"]).is_file())
            persisted = json.loads((output / "extraction-report.json").read_text())
            self.assertEqual(persisted, report)
            self.assertEqual((source / "brief.txt").read_bytes(), original)

    def test_output_inside_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            source.mkdir()

            with self.assertRaisesRegex(ValueError, "outside the source"):
                document_ingest.normalize(source, source / "evidence")

            self.assertFalse((source / "evidence").exists())

    def test_nonempty_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            output = root / "evidence"
            source.mkdir()
            output.mkdir()
            sentinel = output / "keep.txt"
            sentinel.write_text("preserve me", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "refusing silent overwrite"):
                document_ingest.normalize(source, output)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve me")

    def test_symlink_source_is_not_followed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real_source = root / "real-source"
            real_source.mkdir()
            (real_source / "secret.txt").write_text("do not read", encoding="utf-8")
            linked_source = root / "linked-source"
            linked_source.symlink_to(real_source, target_is_directory=True)
            output = root / "evidence"

            with self.assertRaisesRegex(ValueError, "must not be a symbolic link"):
                document_ingest.normalize(linked_source, output)

            self.assertFalse(output.exists())

    def test_unsupported_legacy_office_marks_batch_partial(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            output = root / "evidence"
            source.mkdir()
            (source / "legacy.doc").write_bytes(b"")

            report = document_ingest.normalize(source, output)

            self.assertEqual(report["status"], "PARTIAL")
            self.assertEqual(len(report["sources"]), 1)
            item = report["sources"][0]
            self.assertEqual(item["status"], "UNSUPPORTED")
            self.assertEqual(item["coverage"], "FAILED")
            self.assertEqual(item["method"], "none")
            self.assertEqual(item["reason"], "unsupported legacy Office format")
            self.assertEqual(item["normalized"], None)
            self.assertNotIn("warnings", item)
            self.assertTrue((output / "extraction-report.json").is_file())

    def test_unknown_regular_file_is_registered_as_unsupported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            output = root / "evidence"
            source.mkdir()
            (source / "payload.bin").write_bytes(b"opaque")

            report = document_ingest.normalize(source, output)

            self.assertEqual(report["status"], "PARTIAL")
            self.assertEqual(len(report["sources"]), 1)
            item = report["sources"][0]
            self.assertEqual(item["path"], "payload.bin")
            self.assertEqual(item["format"], "bin")
            self.assertEqual(item["status"], "UNSUPPORTED")
            self.assertEqual(item["coverage"], "FAILED")
            self.assertEqual(item["method"], "none")
            self.assertEqual(item["reason"], "unsupported or unknown format")

    def test_empty_source_directory_is_not_reported_complete(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            output = root / "evidence"
            source.mkdir()

            report = document_ingest.normalize(source, output)

            self.assertEqual(report["status"], "PARTIAL")
            self.assertEqual(report["sources"], [])

    def test_failed_source_uses_reason_without_a_warnings_field(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            output = root / "evidence"
            source.mkdir()
            (source / "corrupt.pdf").write_bytes(b"not a pdf")

            report = document_ingest.normalize(source, output)

            self.assertEqual(report["status"], "PARTIAL")
            self.assertEqual(len(report["sources"]), 1)
            item = report["sources"][0]
            self.assertEqual(item["status"], "FAILED")
            self.assertEqual(item["coverage"], "FAILED")
            self.assertEqual(item["method"], "failed extraction")
            self.assertIn("invalid or truncated PDF", item["reason"])
            self.assertNotIn("warnings", item)

    def test_direct_pdf_copy_has_partial_coverage_without_located_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            output = root / "evidence"
            source.mkdir()
            (source / "brief.pdf").write_bytes(
                b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
            )

            report = document_ingest.normalize(source, output)

            self.assertEqual(report["status"], "PARTIAL")
            item = report["sources"][0]
            self.assertEqual(item["status"], "COMPLETE")
            self.assertEqual(item["coverage"], "PARTIAL")
            self.assertEqual(item["method"], "direct PDF input")
            self.assertEqual(item["normalized"], None)
            self.assertEqual(len(item["assets"]), 1)
            self.assertTrue((output / item["assets"][0]).is_file())
            self.assertIn("not inspected", item["warnings"][0])

    def test_direct_image_copy_has_partial_coverage_without_located_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            output = root / "evidence"
            source.mkdir()
            (source / "diagram.png").write_bytes(
                b"\x89PNG\r\n\x1a\n" + b"0" * 32 + b"IEND\xaeB`\x82"
            )

            report = document_ingest.normalize(source, output)

            self.assertEqual(report["status"], "PARTIAL")
            item = report["sources"][0]
            self.assertEqual(item["status"], "COMPLETE")
            self.assertEqual(item["coverage"], "PARTIAL")
            self.assertEqual(item["method"], "direct image input")
            self.assertEqual(item["normalized"], None)
            self.assertEqual(len(item["assets"]), 1)
            self.assertTrue((output / item["assets"][0]).is_file())
            self.assertIn("not inspected", item["warnings"][0])

    def test_source_failure_after_writes_leaves_no_unreported_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            output = root / "evidence"
            source.mkdir()
            malformed = source / "malformed.docx"
            with ZipFile(malformed, "w") as archive:
                archive.writestr(
                    "word/document.xml",
                    """<?xml version="1.0" encoding="UTF-8"?>
                    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                      <w:body><w:p><w:r><w:t>Readable before late failure</w:t></w:r></w:p></w:body>
                    </w:document>""",
                )
                archive.writestr("word/media/orphan.png", b"artifact written first")
                archive.writestr("custom/_rels/bad.rels", b"<Relationships>")

            report = document_ingest.normalize(source, output)

            self.assertEqual(report["status"], "PARTIAL")
            item = report["sources"][0]
            self.assertEqual(item["status"], "FAILED")
            self.assertEqual(item["coverage"], "FAILED")
            self.assertEqual(item["normalized"], None)
            self.assertEqual(item["assets"], [])
            self.assertFalse((output / "sources" / "S1").exists())
            self.assertFalse((output / "intermediates" / "S1").exists())
            self.assertEqual(
                sorted(path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()),
                ["extraction-report.json"],
            )

    def test_promotion_rejects_unreported_source_artifact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fresh = root / ".evidence-update"
            target = root / "evidence"
            write_promotable_fresh(fresh)
            residue = fresh / "intermediates" / "S1" / "orphan.bin"
            residue.parent.mkdir(parents=True)
            residue.write_bytes(b"unreported")
            target.mkdir()
            sentinel = target / "old-only.txt"
            sentinel.write_text("old evidence", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "unreported artifact"):
                document_ingest.promote_evidence(fresh, target)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "old evidence")
            self.assertTrue(residue.is_file())

    def test_promotion_installs_a_new_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fresh = root / ".evidence-update"
            target = root / "evidence"
            write_promotable_fresh(fresh)

            result = document_ingest.promote_evidence(fresh, target)

            self.assertFalse(fresh.exists())
            self.assertEqual((target / "manifest.md").read_text(), "new evidence")
            report = json.loads((target / "extraction-report.json").read_text())
            self.assertEqual(report["output_root"], str(target.resolve()))
            self.assertEqual(result, {"backup": None, "warning": None})

    def test_promotion_replaces_an_existing_target_without_merging(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fresh = root / ".evidence-update"
            target = root / "evidence"
            write_promotable_fresh(fresh)
            target.mkdir()
            (target / "old-only.txt").write_text("old evidence", encoding="utf-8")

            result = document_ingest.promote_evidence(fresh, target)

            self.assertFalse((target / "old-only.txt").exists())
            self.assertEqual((target / "manifest.md").read_text(), "new evidence")
            self.assertIsNotNone(result["backup"])
            self.assertFalse(Path(result["backup"]).exists())

    def test_invalid_fresh_evidence_preserves_existing_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fresh = root / ".evidence-update"
            target = root / "evidence"
            fresh.mkdir()
            target.mkdir()
            sentinel = target / "old-only.txt"
            sentinel.write_text("old evidence", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "missing manifest.md"):
                document_ingest.promote_evidence(fresh, target)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "old evidence")
            self.assertTrue(fresh.is_dir())

    def test_promotion_failure_restores_existing_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fresh = root / ".evidence-update"
            target = root / "evidence"
            write_promotable_fresh(fresh)
            target.mkdir()
            sentinel = target / "old-only.txt"
            sentinel.write_text("old evidence", encoding="utf-8")
            real_replace = document_ingest.os.replace

            def fail_only_fresh_to_target(source, destination):
                if Path(source) == fresh and Path(destination) == target:
                    raise OSError("simulated promotion failure")
                return real_replace(source, destination)

            with mock.patch.object(
                document_ingest.os,
                "replace",
                side_effect=fail_only_fresh_to_target,
            ):
                with self.assertRaisesRegex(OSError, "simulated promotion failure"):
                    document_ingest.promote_evidence(fresh, target)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "old evidence")
            self.assertTrue(fresh.is_dir())
            self.assertEqual(list(root.glob(".evidence-backup-*")), [])


if __name__ == "__main__":
    unittest.main()
