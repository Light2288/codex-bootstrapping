#!/usr/bin/env python3
"""Normalize local document sources without executing or modifying them."""

import argparse
import json
import os
import shutil
import subprocess
import posixpath
import tempfile
import re
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile


SUPPORTED = {".txt", ".md", ".markdown", ".pdf", ".docx", ".xlsx", ".pptx", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
LEGACY = {".doc", ".xls", ".ppt"}
IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
MAX_XML_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_BYTES = 200 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200
RENDER_TIMEOUT_SECONDS = 120
MAX_XLSX_CELLS = 100000
MAX_TEXT_BYTES = 10 * 1024 * 1024
MAX_DIRECT_BINARY_BYTES = 100 * 1024 * 1024
RELATIONSHIPS_NAMESPACE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
RELATIONSHIP_KIND_URIS = {
    "worksheet": {RELATIONSHIPS_NAMESPACE + "/worksheet", "http://purl.oclc.org/ooxml/officeDocument/relationships/worksheet"},
    "slide": {RELATIONSHIPS_NAMESPACE + "/slide", "http://purl.oclc.org/ooxml/officeDocument/relationships/slide"},
    "notesslide": {RELATIONSHIPS_NAMESPACE + "/notesSlide", "http://purl.oclc.org/ooxml/officeDocument/relationships/notesSlide"},
    "drawing": {RELATIONSHIPS_NAMESPACE + "/drawing", "http://purl.oclc.org/ooxml/officeDocument/relationships/drawing"},
    "table": {RELATIONSHIPS_NAMESPACE + "/table", "http://purl.oclc.org/ooxml/officeDocument/relationships/table"},
    "image": {RELATIONSHIPS_NAMESPACE + "/image", "http://purl.oclc.org/ooxml/officeDocument/relationships/image"},
    "chart": {RELATIONSHIPS_NAMESPACE + "/chart", "http://purl.oclc.org/ooxml/officeDocument/relationships/chart"},
}
RELATIONSHIP_LOCATIONS = {
    "worksheet": ("xl/worksheets/",),
    "slide": ("ppt/slides/",),
    "notesslide": ("ppt/notesSlides/",),
    "drawing": ("xl/drawings/", "word/drawings/"),
    "table": ("xl/tables/",),
    "image": ("xl/media/", "word/media/", "ppt/media/"),
    "chart": ("xl/charts/", "word/charts/", "ppt/charts/"),
}


def local_name(tag):
    return tag.rsplit("}", 1)[-1]


def xml_text(data):
    root = ElementTree.fromstring(data)
    return [text.strip() for text in root.itertext() if text.strip()]


def safe_member(name):
    path = Path(name)
    return not path.is_absolute() and ".." not in path.parts


def validate_archive(archive):
    total = 0
    names = set()
    for info in archive.infolist():
        if info.filename in names:
            raise ValueError("duplicate archive member: {}".format(info.filename))
        names.add(info.filename)
        if info.flag_bits & 0x1:
            raise ValueError("encrypted archive member is unsupported")
        total += info.file_size
        if total > MAX_ARCHIVE_BYTES:
            raise ValueError("archive safety limit: aggregate expanded size exceeds 200 MiB")
        if info.filename.lower().endswith((".xml", ".rels")) and info.file_size > MAX_XML_BYTES:
            raise ValueError("archive safety limit: XML member exceeds 64 MiB")
        if info.file_size > MAX_XML_BYTES and info.compress_size and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
            raise ValueError("archive safety limit: suspicious compression ratio")


def relationships(archive, member):
    path = Path(member)
    rels_name = (path.parent / "_rels" / (path.name + ".rels")).as_posix()
    if rels_name not in archive.namelist():
        return {}
    root = ElementTree.fromstring(archive.read(rels_name))
    result = {}
    for node in root.iter():
        if local_name(node.tag) != "Relationship":
            continue
        relationship_id_value = node.attrib.get("Id")
        if not relationship_id_value:
            raise ValueError("OOXML relationship ID is missing")
        if relationship_id_value in result:
            raise ValueError("duplicate OOXML relationship ID: {}".format(relationship_id_value))
        target = node.attrib.get("Target", "")
        external = node.attrib.get("TargetMode", "").lower() == "external"
        if external:
            resolved = target
        else:
            target_path = PurePosixPath(target)
            if not target or target.startswith("/") or target_path.is_absolute():
                raise ValueError("unsafe internal relationship target")
            combined = posixpath.normpath(posixpath.join(path.parent.as_posix(), target))
            resolved_path = PurePosixPath(combined)
            if combined in {"", ".", ".."} or combined.startswith("../") or resolved_path.is_absolute() or ".." in resolved_path.parts:
                raise ValueError("unsafe internal relationship target")
            resolved = resolved_path.as_posix()
        relationship_type = node.attrib.get("Type", "")
        kind = next((candidate for candidate, uris in RELATIONSHIP_KIND_URIS.items() if relationship_type in uris), None)
        if not external and kind and not any(resolved.startswith(prefix) for prefix in RELATIONSHIP_LOCATIONS[kind]):
            raise ValueError("relationship target has invalid package location for {}".format(kind))
        result[relationship_id_value] = {
            "target": resolved,
            "type": relationship_type,
            "external": external,
            "kind": kind,
        }
    return result


def relationship_target(rels, relationship):
    record = rels.get(relationship)
    return record.get("target") if record else None


def typed_relationship_target(rels, relationship, expected_kind):
    record = rels.get(relationship)
    if not record or record["external"] or record["kind"] != expected_kind.lower():
        return None
    return record["target"]


def archive_has_external_relationships(path):
    with ZipFile(str(path)) as archive:
        validate_archive(archive)
        for member in archive.namelist():
            if member.endswith(".rels"):
                root = ElementTree.fromstring(archive.read(member))
                if any(node.attrib.get("TargetMode", "").lower() == "external" for node in root.iter() if local_name(node.tag) == "Relationship"):
                    return True
    return False


def relationship_id(node):
    return node.attrib.get("{{{}}}id".format(RELATIONSHIPS_NAMESPACE))


def relationship_attribute(key):
    return key.startswith("{{{}}}".format(RELATIONSHIPS_NAMESPACE)) and local_name(key) in {"id", "embed", "link"}


def render_with_libreoffice(source_path, destination):
    """Render DOCX/PPTX to PDF via LibreOffice in headless isolated profile mode."""
    destination = Path(destination).parent / (Path(destination).name + "-libreoffice-render")
    libreoffice = shutil.which("libreoffice") or shutil.which("soffice")
    if not libreoffice:
        return {"rendered": False, "warning": "LibreOffice renderer not found; install LibreOffice for layout rendering"}

    profile_temp = None
    result = None
    try:
        destination.mkdir(parents=True, exist_ok=True)
        profile_temp = tempfile.mkdtemp(prefix=".libreoffice-profile-")
        arguments = [
            libreoffice,
            "--headless",
            "--convert-to", "pdf",
            "--nologo",
            "--norestore",
            "--nofirststartwizard",
            "--outdir", str(destination),
            "-env:UserInstallation={}".format(Path(profile_temp).resolve().as_uri()),
            str(source_path)
        ]

        try:
            subprocess.run(arguments, timeout=RENDER_TIMEOUT_SECONDS, check=True, capture_output=True)
            rendered = destination / (Path(source_path).stem + ".pdf")
            if rendered.exists():
                target = destination / "rendered.pdf"
                rendered.replace(target)
                result = {"rendered": True, "asset": target.relative_to(destination.parent.parent).as_posix()}
            else:
                result = {"rendered": False, "warning": "LibreOffice did not produce output"}
        except subprocess.TimeoutExpired:
            result = {"rendered": False, "warning": "LibreOffice rendering timeout after 120 seconds"}
        except subprocess.CalledProcessError as e:
            result = {"rendered": False, "warning": "LibreOffice rendering failed (exit code {})".format(e.returncode)}
    except OSError as e:
        result = {"rendered": False, "warning": "LibreOffice setup error: {}".format(e)}
    finally:
        if profile_temp is not None:
            try:
                shutil.rmtree(profile_temp)
            except OSError as error:
                cleanup_warning = "LibreOffice temporary profile cleanup failed: {}".format(error)
                if result is None:
                    result = {"rendered": False, "warning": cleanup_warning}
                else:
                    result["warning"] = "{}; {}".format(result.get("warning", "render completed"), cleanup_warning)
    return result


def promote_evidence(fresh, target):
    """Atomically promote fresh to target with swap rollback."""
    fresh = Path(fresh)
    target = Path(target)

    if fresh.is_symlink() or not fresh.is_dir():
        raise ValueError("fresh evidence must be a real directory, not a symbolic link")
    if fresh.resolve() == target.resolve():
        raise ValueError("fresh evidence and target must be different directories")
    if target.is_symlink():
        raise ValueError("target must not be a symbolic link")
    if target.exists() and not target.is_dir():
        raise ValueError("existing target must be a directory")
    for entry in fresh.rglob("*"):
        if entry.is_symlink():
            raise ValueError("fresh evidence contains a symbolic link: {}".format(entry.relative_to(fresh)))

    if fresh.parent.resolve() != target.parent.resolve():
        raise ValueError("fresh evidence and target must be siblings on the same filesystem")

    manifest = fresh / "manifest.md"
    report = fresh / "extraction-report.json"
    if not manifest.is_file() or manifest.stat().st_size == 0:
        raise ValueError("fresh directory missing manifest.md")
    if not report.is_file() or report.stat().st_size == 0:
        raise ValueError("fresh directory missing extraction-report.json")

    try:
        report_data = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError("extraction-report.json must contain valid JSON: {}".format(error))
    if not isinstance(report_data, dict) or not isinstance(report_data.get("sources", []), list):
        raise ValueError("extraction-report.json must contain a sources list")
    if "sources" not in report_data:
        raise ValueError("extraction-report.json must contain a sources list")
    required_root = {"status", "source_root", "output_root", "sources"}
    if not required_root.issubset(report_data):
        raise ValueError("extraction-report.json is missing required root fields")
    if report_data["status"] not in {"COMPLETE", "PARTIAL"}:
        raise ValueError("extraction-report.json status is invalid")
    if not isinstance(report_data["source_root"], str) or not isinstance(report_data["output_root"], str):
        raise ValueError("extraction-report roots must be strings")
    fresh_root = fresh.resolve()
    source_ids = set()
    source_paths = set()
    reported_artifacts = {"manifest.md", "extraction-report.json"}
    for source in report_data.get("sources", []):
        if not isinstance(source, dict):
            raise ValueError("each extraction-report source must be an object")
        required = {"id", "path", "format", "status", "coverage", "method", "assets", "visuals"}
        if not required.issubset(source):
            raise ValueError("each extraction-report source is missing required fields")
        if not all(isinstance(source[key], str) for key in ("id", "path", "format", "status", "coverage", "method")):
            raise ValueError("source provenance/status fields must be strings")
        if source["status"] not in {"COMPLETE", "FAILED", "SKIPPED", "UNSUPPORTED"} or source["coverage"] not in {"COMPLETE", "PARTIAL", "FAILED"}:
            raise ValueError("source status or coverage is invalid")
        if not isinstance(source["visuals"], list):
            raise ValueError("source visuals must be a list")
        if not source["id"] or source["id"] in source_ids or not source["path"] or source["path"] in source_paths:
            raise ValueError("source IDs and paths must be nonempty and unique")
        source_ids.add(source["id"])
        source_paths.add(source["path"])
        if any(not isinstance(visual, dict) or not isinstance(visual.get("owner"), str) or not isinstance(visual.get("target"), str) for visual in source["visuals"]):
            raise ValueError("source visuals must contain owner and target strings")
        if source["status"] == "COMPLETE" and not source.get("normalized") and not source.get("assets"):
            raise ValueError("complete source must reference normalized content or assets")
        if source.get("normalized") is not None and not isinstance(source.get("normalized"), str):
            raise ValueError("source normalized reference must be a string or null")
        if not isinstance(source.get("assets", []), list) or any(not isinstance(asset, str) for asset in source.get("assets", [])):
            raise ValueError("source assets must be a list of strings")
        references = ([source.get("normalized")] if source.get("normalized") else []) + source.get("assets", [])
        for reference in references:
            artifact_path = fresh / reference
            artifact = artifact_path.resolve()
            if artifact_path.is_symlink() or fresh_root not in artifact.parents or not artifact.is_file():
                raise ValueError("referenced artifact is missing or outside fresh evidence: {}".format(reference))
            reported_artifacts.add(Path(reference).as_posix())
    unreported_artifacts = sorted(
        path.relative_to(fresh).as_posix()
        for path in fresh.rglob("*")
        if path.is_file() and path.relative_to(fresh).as_posix() not in reported_artifacts
    )
    if unreported_artifacts:
        raise ValueError("fresh evidence contains unreported artifact: {}".format(unreported_artifacts[0]))
    valid_pairs = {("COMPLETE", "COMPLETE"), ("COMPLETE", "PARTIAL"), ("FAILED", "FAILED"), ("SKIPPED", "FAILED"), ("UNSUPPORTED", "FAILED")}
    if any((source["status"], source["coverage"]) not in valid_pairs for source in report_data["sources"]):
        raise ValueError("source status and coverage are inconsistent")
    if any(source["status"] != "COMPLETE" or source["coverage"] != "COMPLETE" for source in report_data["sources"]) and report_data["status"] != "PARTIAL":
        raise ValueError("overall status must be PARTIAL when any source is not fully complete")
    backup_container = None
    backup = None

    if target.exists():
        backup_container = Path(tempfile.mkdtemp(prefix=".{}-backup-".format(target.name), dir=str(target.parent)))
        backup = backup_container / "previous"
        try:
            os.replace(str(target), str(backup))
        except OSError:
            backup_container.rmdir()
            raise

    try:
        os.replace(str(fresh), str(target))
    except OSError as promotion_error:
        if backup is not None and backup.exists():
            try:
                os.replace(str(backup), str(target))
            except OSError as rollback_error:
                raise RuntimeError(
                    "promotion failed: {}; rollback failed from {}: {}".format(
                        promotion_error, backup, rollback_error
                    )
                ) from rollback_error
            backup_container.rmdir()
        raise

    promoted_report = target / "extraction-report.json"
    temporary_report = target / "extraction-report.json.tmp"
    report_data["output_root"] = str(target.resolve())
    try:
        temporary_report.write_text(json.dumps(report_data, indent=2) + "\n", encoding="utf-8")
        os.replace(str(temporary_report), str(promoted_report))
    except OSError as metadata_error:
        rollback_errors = []
        if target.exists():
            try:
                os.replace(str(target), str(fresh))
            except OSError as error:
                rollback_errors.append("fresh restore failed: {}".format(error))
        if backup is not None and backup.exists():
            try:
                os.replace(str(backup), str(target))
                backup_container.rmdir()
            except OSError as error:
                rollback_errors.append("backup restore failed: {}".format(error))
        if rollback_errors:
            raise RuntimeError("metadata failed: {}; rollback failed: {}".format(metadata_error, "; ".join(rollback_errors))) from metadata_error
        raise metadata_error

    warning = None
    if backup is not None and backup.exists():
        try:
            shutil.rmtree(str(backup_container))
        except OSError as error:
            warning = "promotion succeeded but backup cleanup failed: {}".format(error)

    return {"backup": str(backup) if backup is not None else None, "warning": warning}


def write_markdown(output, source_id, heading, lines):
    relative = Path("sources") / source_id / "content.md"
    target = output / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# {}\n\n{}\n".format(heading, "\n\n".join(lines)), encoding="utf-8")
    return relative.as_posix()


def extract_media(archive, prefix, output, source_id):
    assets = []
    asset_root = (output / "intermediates" / source_id).resolve()
    members = [name for name in sorted(archive.namelist()) if name.startswith(prefix) and not name.endswith("/")]
    validated = []
    targets = set()
    for name in members:
        if not safe_member(name):
            raise ValueError("unsafe media member: {}".format(name))
        member_relative = Path(name[len(prefix):])
        if member_relative.is_absolute() or ".." in member_relative.parts:
            raise ValueError("unsafe media member: {}".format(name))
        relative = Path("intermediates") / source_id / member_relative
        target = (output / relative).resolve()
        if target == asset_root or asset_root not in target.parents:
            raise ValueError("unsafe media member: {}".format(name))
        if target in targets:
            raise ValueError("duplicate media target: {}".format(target.relative_to(asset_root)))
        if any(existing in target.parents or target in existing.parents for existing in targets):
            raise ValueError("media target hierarchy collision: {}".format(target.relative_to(asset_root)))
        targets.add(target)
        validated.append((name, relative, target))
    output.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".{}-media-".format(source_id), dir=str(output)))
    try:
        for name, relative, target in validated:
            staged = staging / relative.relative_to(Path("intermediates") / source_id)
            staged.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(name) as source, staged.open("wb") as destination:
                shutil.copyfileobj(source, destination, length=1024 * 1024)
        if validated:
            asset_root.parent.mkdir(parents=True, exist_ok=True)
            os.replace(str(staging), str(asset_root))
            staging = None
        assets.extend(relative.as_posix() for name, relative, target in validated)
    finally:
        if staging is not None and staging.exists():
            shutil.rmtree(str(staging))
    return assets, [name for name, _, _ in validated]


def extract_selected_media(archive, members, output, source_id, prefix="ppt/media/"):
    if not members:
        return [], []
    selected = set(members)

    class SelectedArchive:
        def namelist(self):
            return sorted(selected)

        def open(self, name):
            return archive.open(name)

    return extract_media(SelectedArchive(), prefix, output, source_id)


def normalize_docx(path, output, source_id):
    with ZipFile(str(path)) as archive:
        validate_archive(archive)
        data = archive.read("word/document.xml")
        root = ElementTree.fromstring(data)
        rels = relationships(archive, "word/document.xml")
        lines = []
        paragraph = 0
        table = 0
        visuals = []
        warnings = []
        body = next((node for node in root.iter() if local_name(node.tag) == "body"), root)
        for node in list(body):
            kind = local_name(node.tag)
            if kind == "p":
                paragraph += 1
                for drawing in (item for item in node.iter() if local_name(item.tag) == "drawing"):
                    for related in drawing.iter():
                        for key, relationship in related.attrib.items():
                            if not relationship_attribute(key):
                                continue
                            if relationship not in rels:
                                warnings.append("unresolved visual relationship in DOCX paragraph {}: {}".format(paragraph, relationship))
                                continue
                            record = rels[relationship]
                            if record["external"] or record["kind"] not in {"image", "chart"}:
                                continue
                            target = record["target"]
                            if target in archive.namelist() and not any(visual["target"] == target and visual["owner"] == "DOCX paragraph {}".format(paragraph) for visual in visuals):
                                visuals.append({"owner": "DOCX paragraph {}".format(paragraph), "target": target})
                            elif target not in archive.namelist():
                                warnings.append("unresolved visual relationship target in DOCX paragraph {}: {}".format(paragraph, target))
                text = " ".join(xml_text(ElementTree.tostring(node, encoding="utf-8")))
                if text:
                    lines.append("- DOCX paragraph {}: {}".format(paragraph, text))
            elif kind == "tbl":
                table += 1
                text = " | ".join(xml_text(ElementTree.tostring(node, encoding="utf-8")))
                if text:
                    lines.append("- DOCX table {}: {}".format(table, text))
        assets, media_files = extract_media(archive, "word/media/", output, source_id)

        for media_file in media_files:
            if not any(v["target"] == media_file for v in visuals):
                visuals.append({
                    "owner": "unreferenced package media",
                    "target": media_file
                })

    if assets:
        lines.append("- Embedded visuals: {}".format(", ".join(assets)))
    return write_markdown(output, source_id, path.name, lines or ["No readable text found."]), assets, visuals, warnings


def shared_strings(archive):
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    return [" ".join(text.strip() for text in node.itertext() if text.strip()) for node in root if local_name(node.tag) == "si"]


def workbook_sheets(archive):
    root = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    rels = relationships(archive, "xl/workbook.xml")
    sheets = []
    for index, node in enumerate((item for item in root.iter() if local_name(item.tag) == "sheet"), 1):
        target = typed_relationship_target(rels, relationship_id(node), "worksheet")
        sheets.append((node.attrib.get("name", "Sheet {}".format(index)), target, node.attrib.get("state", "visible")))
    return sheets


def column_name(index):
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(ord("A") + remainder) + name
    return name


def xlsx_styles(archive):
    styles = {}
    custom_formats = {}
    if "xl/styles.xml" not in archive.namelist():
        return styles
    root = ElementTree.fromstring(archive.read("xl/styles.xml"))
    for node in root.iter():
        if local_name(node.tag) == "numFmt":
            custom_formats[int(node.attrib.get("numFmtId", "0"))] = node.attrib.get("formatCode", "")
    cell_formats = next((node for node in root.iter() if local_name(node.tag) == "cellXfs"), None)
    if cell_formats is not None:
        for index, node in enumerate(cell_formats):
            if local_name(node.tag) == "xf":
                number_format = int(node.attrib.get("numFmtId", "0"))
                styles[str(index)] = (number_format, custom_formats.get(number_format, ""))
    return styles


def strip_number_format_literals(format_code):
    result = []
    quoted = False
    bracketed = False
    escaped = False
    for character in format_code:
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if character == '"' and not bracketed:
            quoted = not quoted
            continue
        if character == "[" and not quoted:
            bracketed = True
            continue
        if character == "]" and bracketed:
            bracketed = False
            continue
        if not quoted and not bracketed:
            result.append(character)
    return "".join(result).lower()


def xlsx_value(cell, strings, styles, date_1904, warnings):
    cell_type = cell.attrib.get("t", "")
    raw = next((node.text or "" for node in cell if local_name(node.tag) == "v"), "")
    if cell_type == "inlineStr":
        return " ".join((node.text or "").strip() for node in cell.iter() if local_name(node.tag) == "t" and (node.text or "").strip())
    if cell_type == "s":
        if raw.isdigit() and int(raw) < len(strings):
            return strings[int(raw)]
        warnings.append("invalid shared string index at {}".format(cell.attrib.get("r", "unknown")))
        return "UNRESOLVED SHARED STRING {}".format(raw)
    if cell_type == "b":
        if raw in {"0", "1"}:
            return "TRUE" if raw == "1" else "FALSE"
        warnings.append("invalid boolean at {}".format(cell.attrib.get("r", "unknown")))
        return "AMBIGUOUS BOOLEAN {}".format(raw)
    if cell_type == "e":
        return "ERROR {}".format(raw)
    if cell_type == "str":
        return raw
    number_format, format_code = styles.get(cell.attrib.get("s", "0"), (0, ""))
    if number_format in {18, 19, 20, 21, 45, 47}:
        warnings.append("time formatting retained as raw serial at {}".format(cell.attrib.get("r", "unknown")))
        return "TIME {}".format(raw)
    if number_format == 46:
        warnings.append("elapsed duration retained as raw serial at {}".format(cell.attrib.get("r", "unknown")))
        return "ELAPSED {}".format(raw)
    semantic_format = strip_number_format_literals(format_code)
    date_format = number_format in {14, 15, 16, 17, 18, 19, 20, 21, 22, 45, 46, 47} or any(token in semantic_format for token in ("yy", "dd", "hh", "ss"))
    if date_format:
        try:
            serial = float(raw)
            if not date_1904 and serial == 60:
                warnings.append("ambiguous Excel 1900 leap-day serial at {}".format(cell.attrib.get("r", "unknown")))
                return "AMBIGUOUS EXCEL DATE 60"
            if date_1904:
                value = datetime(1904, 1, 1) + timedelta(days=serial)
            else:
                base = datetime(1899, 12, 31)
                value = base + timedelta(days=serial if serial < 60 else serial - 1)
            return value.strftime("%Y-%m-%d" if serial.is_integer() else "%Y-%m-%dT%H:%M:%S")
        except (ValueError, OverflowError):
            warnings.append("unreadable date/time serial at {}".format(cell.attrib.get("r", "unknown")))
            return "AMBIGUOUS DATE/TIME {}".format(raw)
    if cell_type not in {"", "n"}:
        warnings.append("unsupported XLSX cell type {} at {}".format(cell_type, cell.attrib.get("r", "unknown")))
        return "UNSUPPORTED {} {}".format(cell_type, raw)
    return raw


def normalize_xlsx(path, output, source_id):
    with ZipFile(str(path)) as archive:
        validate_archive(archive)
        strings = shared_strings(archive)
        sheets = workbook_sheets(archive)
        styles = xlsx_styles(archive)
        workbook_root = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        workbook_properties = next((node for node in workbook_root.iter() if local_name(node.tag) == "workbookPr"), None)
        date_1904 = workbook_properties is not None and workbook_properties.attrib.get("date1904") in {"1", "true"}
        lines = []
        visuals = []
        warnings = []
        owned_tables = set()
        owned_charts = set()
        parsed_sheets = []

        for sheet, member, visibility in sheets:
            if not member or member not in archive.namelist():
                lines.append("- {}: worksheet relationship target unavailable".format(sheet))
                warnings.append("worksheet relationship target unavailable for {}".format(sheet))
                continue
            heading = "## Sheet: {}".format(sheet)
            if visibility != "visible":
                heading += " (visibility: {})".format(visibility)
            lines.append(heading)
            root = ElementTree.fromstring(archive.read(member))
            sheet_rels = relationships(archive, member)
            parsed_sheets.append((sheet, root, sheet_rels))
            for table_part in (node for node in root.iter() if local_name(node.tag) == "tablePart"):
                target = typed_relationship_target(sheet_rels, relationship_id(table_part), "table")
                if target in archive.namelist():
                    table_root = ElementTree.fromstring(archive.read(target))
                    table_name = table_root.attrib.get("name", Path(target).stem)
                    table_range = table_root.attrib.get("ref", "unknown")
                    lines.append("- {} table {} range {}".format(sheet, table_name, table_range))
                    owned_tables.add(target)
                else:
                    warnings.append("unresolved table relationship on sheet {}".format(sheet))
            dimension = next((node.attrib.get("ref") for node in root.iter() if local_name(node.tag) == "dimension"), None)
            if dimension:
                lines.append("- dimension: {}".format(dimension))
            hidden_columns = []
            for column in (node for node in root.iter() if local_name(node.tag) == "col" and node.attrib.get("hidden") in {"1", "true"}):
                start = int(column.attrib.get("min", "1"))
                end = int(column.attrib.get("max", str(start)))
                hidden_columns.append("{}:{}".format(column_name(start), column_name(end)))
            if hidden_columns:
                lines.append("- hidden columns: {}".format(", ".join(hidden_columns)))
            for row in (node for node in root.iter() if local_name(node.tag) == "row" and node.attrib.get("hidden") in {"1", "true"}):
                lines.append("- hidden row: {}".format(row.attrib.get("r", "unknown")))
            filter_range = next((node.attrib.get("ref") for node in root.iter() if local_name(node.tag) == "autoFilter"), None)
            if filter_range:
                lines.append("- filter: {}".format(filter_range))
            shared_formulas = {}
            shared_followers = []
            cells = [node for node in root.iter() if local_name(node.tag) == "c"]
            if len(cells) > MAX_XLSX_CELLS:
                raise ValueError("XLSX worksheet cell limit exceeds {}".format(MAX_XLSX_CELLS))
            for cell in cells:
                formula_node = next((node for node in cell if local_name(node.tag) == "f"), None)
                if formula_node is not None and formula_node.attrib.get("t") == "shared":
                    shared_id = formula_node.attrib.get("si", "unknown")
                    if formula_node.text:
                        shared_formulas[shared_id] = (cell.attrib.get("r", "unknown"), formula_node.text)
                    else:
                        shared_followers.append((shared_id, cell.attrib.get("r", "unknown")))
            for cell in cells:
                ref = cell.attrib.get("r", "unknown")
                formula_node = next((node for node in cell if local_name(node.tag) == "f"), None)
                formula = formula_node.text or "" if formula_node is not None else ""
                value = xlsx_value(cell, strings, styles, date_1904, warnings)
                detail = "{} = {}".format(ref, value)
                if formula:
                    detail += " (Formula: {})".format(formula)
                lines.append("- {} range {}".format(sheet, detail))
            for shared_id, (anchor, formula) in sorted(shared_formulas.items()):
                lines.append("- shared formula {} anchor: {} ({})".format(shared_id, anchor, formula))
            for shared_id, follower in shared_followers:
                lines.append("- shared formula {} follower: {}".format(shared_id, follower))
                warnings.append("shared formula follower {} at {} was not translated".format(shared_id, follower))

        referenced_visuals = set()
        for sheet, sheet_root, sheet_rels in parsed_sheets:
            for drawing_elem in sheet_root.iter():
                if local_name(drawing_elem.tag) == "drawing":
                    drawing_ref = relationship_id(drawing_elem)

                    if not drawing_ref or drawing_ref not in sheet_rels:
                        warnings.append("unresolved drawing relationship on sheet {}".format(sheet))
                        continue

                    drawing_target = typed_relationship_target(sheet_rels, drawing_ref, "drawing")
                    if drawing_target not in archive.namelist():
                        warnings.append("unresolved drawing relationship target on sheet {}".format(sheet))
                        continue

                    drawing_data = archive.read(drawing_target)
                    drawing_elem_doc = ElementTree.fromstring(drawing_data)

                    for anchor_elem in drawing_elem_doc.iter():
                        anchor_kind = local_name(anchor_elem.tag)
                        if anchor_kind in ("twoCellAnchor", "oneCellAnchor", "absoluteAnchor"):
                            anchor_range = ""
                            absolute_location = ""
                            if anchor_kind == "absoluteAnchor":
                                position = next((e for e in anchor_elem if local_name(e.tag) == "pos"), None)
                                extent = next((e for e in anchor_elem if local_name(e.tag) == "ext"), None)
                                if position is None or extent is None or not all(key in position.attrib for key in ("x", "y")) or not all(key in extent.attrib for key in ("cx", "cy")):
                                    warnings.append("uninterpretable absoluteAnchor on sheet {}".format(sheet))
                                else:
                                    try:
                                        x, y, cx, cy = (int(position.attrib["x"]), int(position.attrib["y"]), int(extent.attrib["cx"]), int(extent.attrib["cy"]))
                                        if x < 0 or y < 0 or cx <= 0 or cy <= 0:
                                            raise ValueError
                                        absolute_location = "absolute position x={} y={} extent cx={} cy={}".format(x, y, cx, cy)
                                    except ValueError:
                                        warnings.append("uninterpretable absoluteAnchor on sheet {}".format(sheet))
                            elif anchor_kind == "oneCellAnchor":
                                from_elem = next((e for e in anchor_elem if local_name(e.tag) == "from"), None)
                                extent = next((e for e in anchor_elem if local_name(e.tag) == "ext"), None)
                                if from_elem is None or extent is None or not all(key in extent.attrib for key in ("cx", "cy")):
                                    warnings.append("uninterpretable oneCellAnchor on sheet {}".format(sheet))
                                else:
                                    try:
                                        start_col = next(int(e.text or "0") for e in from_elem if local_name(e.tag) == "col")
                                        start_row = next(int(e.text or "0") for e in from_elem if local_name(e.tag) == "row")
                                        cx, cy = int(extent.attrib["cx"]), int(extent.attrib["cy"])
                                        if not (0 <= start_col <= 16383 and 0 <= start_row <= 1048575 and cx > 0 and cy > 0):
                                            raise ValueError
                                        absolute_location = "start {}{} extent cx={} cy={}".format(column_name(start_col + 1), start_row + 1, cx, cy)
                                    except (ValueError, StopIteration):
                                        warnings.append("uninterpretable oneCellAnchor on sheet {}".format(sheet))
                            from_elem = next((e for e in anchor_elem if local_name(e.tag) == "from"), None)
                            to_elem = next((e for e in anchor_elem if local_name(e.tag) == "to"), None)
                            if anchor_kind != "absoluteAnchor" and from_elem is not None and to_elem is not None:
                                from_col = next((int(e.text or "0") for e in from_elem if local_name(e.tag) == "col"), 0)
                                from_row = next((int(e.text or "0") for e in from_elem if local_name(e.tag) == "row"), 0)
                                to_col = next((int(e.text or "0") for e in to_elem if local_name(e.tag) == "col"), 0)
                                to_row = next((int(e.text or "0") for e in to_elem if local_name(e.tag) == "row"), 0)
                                if not (0 <= from_col <= 16383 and 0 <= to_col <= 16383 and 0 <= from_row <= 1048575 and 0 <= to_row <= 1048575):
                                    raise ValueError("drawing anchor is outside XLSX row/column bounds")
                                from_col_letter = column_name(from_col + 1)
                                to_col_letter = column_name(to_col + 1)
                                anchor_range = "{}{}:{}{}".format(from_col_letter, from_row + 1, to_col_letter, to_row + 1)
                            drawing_rels = relationships(archive, drawing_target)
                            relationship_ids = set()
                            for related in anchor_elem.iter():
                                relationship_ids.update(value for key, value in related.attrib.items() if relationship_attribute(key))
                            for relationship in sorted(relationship_ids):
                                record = drawing_rels.get(relationship)
                                if record and (record["external"] or record["kind"] not in {"image", "chart"}):
                                    continue
                                rel_target = record["target"] if record else None
                                if rel_target in archive.namelist():
                                    owner_text = "XLSX sheet {}".format(sheet)
                                    if anchor_range:
                                        owner_text += " {}".format(anchor_range)
                                    elif absolute_location:
                                        owner_text += " {}".format(absolute_location)
                                    visuals.append({"owner": owner_text, "target": rel_target})
                                    referenced_visuals.add(rel_target)
                                    if rel_target.startswith("xl/charts/"):
                                        labels = " ".join(xml_text(archive.read(rel_target)))
                                        lines.append("- {} chart {}: {}".format(sheet, anchor_range or absolute_location or "unlocated", labels or "chart definition extracted"))
                                        owned_charts.add(rel_target)
                                else:
                                    warning_type = "unresolved absoluteAnchor relationship" if anchor_kind == "absoluteAnchor" else "unresolved drawing relationship"
                                    warnings.append("{} on sheet {}".format(warning_type, sheet))

        charts = sorted(name for name in archive.namelist() if name.startswith("xl/charts/") and name.endswith(".xml"))
        tables = sorted(name for name in archive.namelist() if name.startswith("xl/tables/") and name.endswith(".xml"))
        for member in tables:
            if member in owned_tables:
                continue
            warnings.append("unreferenced package table omitted: {}".format(Path(member).name))
        for member in charts:
            if member in owned_charts:
                continue
            warnings.append("unreferenced package chart omitted: {}".format(Path(member).name))
        owned_media = referenced_visuals & set(name for name in archive.namelist() if name.startswith("xl/media/"))
        assets, _ = extract_selected_media(archive, owned_media, output, source_id, "xl/media/")


    return write_markdown(output, source_id, path.name, lines or ["No visible cells found."]), assets, visuals, warnings


def normalize_pptx(path, output, source_id):
    with ZipFile(str(path)) as archive:
        validate_archive(archive)
        slides = []
        warnings = []
        presentation_present = "ppt/presentation.xml" in archive.namelist()
        if presentation_present:
            root = ElementTree.fromstring(archive.read("ppt/presentation.xml"))
            rels = relationships(archive, "ppt/presentation.xml")
            declared_slides = []
            for node in (item for item in root.iter() if local_name(item.tag) == "sldId"):
                record = rels.get(relationship_id(node))
                declared_slides.append(record if record and record["kind"] == "slide" else None)
            for ordinal, record in enumerate(declared_slides, 1):
                if record and record["external"]:
                    warnings.append("external slide relationship for slide {} was not ingested".format(ordinal))
                    continue
                member = record["target"] if record else None
                if member in archive.namelist():
                    slides.append((ordinal, member))
                else:
                    warnings.append("missing slide {} relationship target: {}".format(ordinal, member or "unresolved"))
        if not slides and not presentation_present:
            fallback_members = sorted((name for name in archive.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml")), key=lambda name: int(Path(name).stem.replace("slide", "")))
            slides = [(index, member) for index, member in enumerate(fallback_members, 1)]
            if slides:
                warnings.append("presentation.xml absent; filename-based slide fallback used")
        lines = []
        visuals = []
        referenced_visuals = set()
        reachable_media = set()
        reachable_charts = set()
        for ordinal, member in slides:
            lines.append("## Slide {}\n\n{}".format(ordinal, " ".join(xml_text(archive.read(member))) or "No visible text."))
            slide_relationships = relationships(archive, member)
            note_member = next((record["target"] for record in slide_relationships.values() if not record["external"] and record["kind"] == "notesslide"), None)
            if note_member and note_member in archive.namelist():
                note = " ".join(xml_text(archive.read(note_member)))
                if note:
                    lines.append("- Slide {} speaker notes: {}".format(ordinal, note))
            elif note_member:
                warnings.append("missing speaker notes relationship target on slide {}".format(ordinal))

            slide_rels = slide_relationships
            slide_root = ElementTree.fromstring(archive.read(member))

            for elem in slide_root.iter():
                for key, relationship in elem.attrib.items():
                    if not relationship_attribute(key):
                        continue
                    target = relationship_target(slide_rels, relationship)
                    record = slide_rels.get(relationship)
                    visual_kind = record["kind"] if record else ""
                    if record and not record["external"] and visual_kind in {"image", "chart"} and target in archive.namelist():
                        visuals.append({"owner": "PPTX slide {}".format(ordinal), "target": target})
                        referenced_visuals.add(target)
                        if target.startswith("ppt/media/"):
                            reachable_media.add(target)
                        else:
                            reachable_charts.add(target)
                    elif record and not record["external"] and visual_kind in {"image", "chart"} and target:
                        warnings.append("missing visual relationship target on slide {}: {}".format(ordinal, target))
                    elif target is None:
                        warnings.append("unresolved visual relationship on slide {}: {}".format(ordinal, relationship))

        charts = sorted(reachable_charts if presentation_present else (name for name in archive.namelist() if name.startswith("ppt/charts/") and name.endswith(".xml")))
        for index, member in enumerate(charts, 1):
            lines.append("- Presentation chart {}: {}".format(index, " ".join(xml_text(archive.read(member))) or "chart definition extracted"))
        if presentation_present:
            assets, media_files = extract_selected_media(archive, reachable_media, output, source_id)
        else:
            assets, media_files = extract_media(archive, "ppt/media/", output, source_id)

        for media_file in media_files:
            if media_file not in referenced_visuals:
                visuals.append({
                    "owner": "unreferenced package media",
                    "target": media_file
                })
        for chart in charts:
            if chart not in referenced_visuals:
                visuals.append({"owner": "unreferenced package chart", "target": chart})
    if assets:
        lines.append("- Embedded visuals: {}".format(", ".join(assets)))
    return write_markdown(output, source_id, path.name, lines or ["No visible slide content found."]), assets, visuals, warnings


def normalize_one(path, output, source_id):
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".markdown"}:
        if path.stat().st_size > MAX_TEXT_BYTES:
            raise ValueError("direct text size limit exceeds {} bytes".format(MAX_TEXT_BYTES))
        text = path.read_text(encoding="utf-8")
        return write_markdown(output, source_id, path.name, [text]), [], "direct text read", [], []
    if suffix == ".docx":
        normalized, assets, visuals, warnings = normalize_docx(path, output, source_id)
        return normalized, assets, "OOXML text, table, and media extraction", visuals, warnings
    if suffix == ".xlsx":
        normalized, assets, visuals, warnings = normalize_xlsx(path, output, source_id)
        return normalized, assets, "OOXML sheets, cells, formulas, tables, and chart extraction", visuals, warnings
    if suffix == ".pptx":
        normalized, assets, visuals, warnings = normalize_pptx(path, output, source_id)
        return normalized, assets, "OOXML slides, notes, charts, and media extraction", visuals, warnings
    relative = Path("intermediates") / source_id / path.name
    size = path.stat().st_size
    if size > MAX_DIRECT_BINARY_BYTES:
        raise ValueError("direct attachment size limit exceeds {} bytes".format(MAX_DIRECT_BINARY_BYTES))
    target = output / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with path.open("rb") as source_file:
        prefix = source_file.read(16)
    if suffix == ".pdf":
        with path.open("rb") as source_file:
            source_file.seek(max(0, path.stat().st_size - 1024))
            trailer = source_file.read(1024)
        if not prefix.startswith(b"%PDF-") or b"%%EOF" not in trailer:
            raise ValueError("invalid or truncated PDF")
    image_signatures = {
        ".png": (b"\x89PNG\r\n\x1a\n",),
        ".jpg": (b"\xff\xd8\xff",),
        ".jpeg": (b"\xff\xd8\xff",),
        ".gif": (b"GIF87a", b"GIF89a"),
        ".webp": (b"RIFF",),
    }
    if suffix in image_signatures and not any(prefix.startswith(signature) for signature in image_signatures[suffix]):
        raise ValueError("invalid {} signature".format(suffix.lstrip(".").upper()))
    if suffix == ".webp" and prefix[8:12] != b"WEBP":
        raise ValueError("invalid WEBP signature")
    with path.open("rb") as source_file:
        source_file.seek(max(0, size - 12))
        tail = source_file.read(12)
    if suffix == ".png" and (size < 33 or not tail.endswith(b"IEND\xaeB`\x82")):
        raise ValueError("invalid or truncated PNG")
    if suffix in {".jpg", ".jpeg"} and (size < 4 or not tail.endswith(b"\xff\xd9")):
        raise ValueError("invalid or truncated JPEG")
    if suffix == ".gif" and (size < 14 or not tail.endswith(b";")):
        raise ValueError("invalid or truncated GIF")
    if suffix == ".webp" and size < 20:
        raise ValueError("invalid or truncated WEBP")
    if suffix == ".svg":
        if size > MAX_XML_BYTES:
            raise ValueError("SVG size limit exceeds 64 MiB")
        try:
            svg_root = ElementTree.parse(str(path)).getroot()
        except ElementTree.ParseError as error:
            raise ValueError("invalid SVG XML: {}".format(error))
        if local_name(svg_root.tag).lower() != "svg":
            raise ValueError("invalid SVG root element")
        for element in svg_root.iter():
            if local_name(element.tag).lower() in {"script", "foreignobject"}:
                raise ValueError("unsafe active SVG element")
            for key, value in element.attrib.items():
                name = local_name(key).lower()
                if "\\" in value:
                    raise ValueError("unsafe SVG CSS escape")
                if name.startswith("on"):
                    raise ValueError("unsafe SVG event handler")
                if name in {"href", "src"} and value and (value.startswith("data:") or not value.startswith("#")):
                    raise ValueError("unsafe external SVG reference")
                if any(not reference.strip(" \t\r\n\"'").startswith("#") for reference in re.findall(r"url\(([^)]+)\)", value, re.IGNORECASE)):
                    raise ValueError("unsafe external SVG URL reference")
            if local_name(element.tag).lower() == "style":
                css = "".join(element.itertext())
                if "\\" in css:
                    raise ValueError("unsafe SVG CSS escape")
                if "@import" in css.lower() or any(not reference.strip(" \t\r\n\"'").startswith("#") for reference in re.findall(r"url\(([^)]+)\)", css, re.IGNORECASE)):
                    raise ValueError("unsafe external SVG CSS reference")
    shutil.copyfile(str(path), str(target))
    method = "direct PDF input" if suffix == ".pdf" else "direct image input"
    warnings = ["content was copied but not inspected or extracted into located evidence"]
    return None, [relative.as_posix()], method, [], warnings


def normalize(source, output):
    source = Path(source)
    output = Path(output)
    if source.is_symlink():
        raise ValueError("source must not be a symbolic link")
    if output.is_symlink():
        raise ValueError("output must not be a symbolic link")
    source = source.resolve()
    output = output.resolve()
    if not source.is_dir():
        raise ValueError("input must be an existing local directory")
    if output == source or source in output.parents:
        raise ValueError("output must be outside the source directory")
    if output.exists() and any(output.iterdir()):
        raise ValueError("output directory must be absent or empty; refusing silent overwrite")
    output.mkdir(parents=True, exist_ok=True)
    try:
        paths = []
        symlinks = []
        for path in source.rglob("*"):
            if path.is_symlink():
                symlinks.append(path)
                continue
            if path.is_file():
                paths.append(path)
        paths.extend(symlinks)
        paths.sort(key=lambda path: path.relative_to(source).as_posix())
        report = {"status": "COMPLETE" if paths else "PARTIAL", "source_root": str(source), "output_root": str(output), "sources": []}
        for index, path in enumerate(paths, 1):
            source_id = "S{}".format(index)
            relative = path.relative_to(source).as_posix()
            item = {"id": source_id, "path": relative, "format": path.suffix.lower().lstrip(".")}
            if path.is_symlink():
                item.update(status="SKIPPED", coverage="FAILED", reason="symbolic link is not followed", method="none", normalized=None, assets=[], visuals=[])
                report["status"] = "PARTIAL"
            elif path.suffix.lower() in LEGACY:
                item.update(status="UNSUPPORTED", coverage="FAILED", reason="unsupported legacy Office format", method="none", normalized=None, assets=[], visuals=[])
                report["status"] = "PARTIAL"
            elif path.suffix.lower() not in SUPPORTED:
                item.update(status="UNSUPPORTED", coverage="FAILED", reason="unsupported or unknown format", method="none", normalized=None, assets=[], visuals=[])
                report["status"] = "PARTIAL"
            else:
                source_output = Path(tempfile.mkdtemp(prefix=".{}-source-".format(source_id), dir=str(output)))
                try:
                    try:
                        result = normalize_one(path, source_output, source_id)
                        normalized, assets, method, visuals, warnings = result
                        warnings = list(warnings)
                        coverage = "PARTIAL" if warnings else "COMPLETE"
                        rendered = False

                        if path.suffix.lower() in {".docx", ".xlsx", ".pptx"}:
                            if archive_has_external_relationships(path):
                                warnings.append("external relationships prevented safe rendering")
                                coverage = "PARTIAL"
                            else:
                                destination = source_output / "intermediates" / source_id
                                render_result = render_with_libreoffice(path, destination)
                                if render_result.get("rendered"):
                                    asset_path = render_result.get("asset", "")
                                    if asset_path:
                                        assets.append(asset_path)
                                    rendered = True
                                    if render_result.get("warning"):
                                        warnings.append(render_result["warning"])
                                        coverage = "PARTIAL"
                                else:
                                    render_warning = render_result.get("warning", "rendering failed")
                                    warnings.append(render_warning)
                                    coverage = "PARTIAL"

                        if path.suffix.lower() in {".docx", ".xlsx", ".pptx"} and not rendered:
                            warnings.append("layout rendering not performed")
                            coverage = "PARTIAL"

                        if coverage == "PARTIAL":
                            report["status"] = "PARTIAL"

                        item.update(status="COMPLETE", coverage=coverage, method=method, normalized=normalized, assets=assets, visuals=visuals, warnings=warnings)
                        for staged_artifact in sorted(source_output.rglob("*")):
                            if not staged_artifact.is_file():
                                continue
                            destination = output / staged_artifact.relative_to(source_output)
                            destination.parent.mkdir(parents=True, exist_ok=True)
                            os.replace(str(staged_artifact), str(destination))
                    finally:
                        shutil.rmtree(str(source_output))
                except OSError as error:
                    failed_path = Path(error.filename).resolve() if error.filename else None
                    if failed_path is None or (failed_path != source and source not in failed_path.parents):
                        raise
                    item.update(status="FAILED", coverage="FAILED", reason="unreadable {}: {}".format(path.suffix.lower().lstrip("."), error), method="failed extraction", normalized=None, assets=[], visuals=[])
                    report["status"] = "PARTIAL"
                except (BadZipFile, KeyError, ElementTree.ParseError, UnicodeError, ValueError) as error:
                    item.update(status="FAILED", coverage="FAILED", reason="unreadable {}: {}".format(path.suffix.lower().lstrip("."), error), method="failed extraction", normalized=None, assets=[], visuals=[])
                    report["status"] = "PARTIAL"
            report["sources"].append(item)
        (output / "extraction-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return report
    except Exception as normalization_error:
        try:
            shutil.rmtree(str(output))
        except OSError as cleanup_error:
            raise RuntimeError(
                "normalization failed: {}; cleanup failed for {}: {}".format(
                    normalization_error, output, cleanup_error
                )
            ) from cleanup_error
        raise


def check_dependencies():
    libreoffice = shutil.which("libreoffice") or shutil.which("soffice")
    result = {
        "required": {"python": "available (standard-library OOXML extraction)"},
        "optional": {"libreoffice": "available" if libreoffice else "missing; install LibreOffice for layout/PDF rendering"},
    }
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check-dependencies")
    normalize_parser = subparsers.add_parser("normalize")
    normalize_parser.add_argument("source", type=Path)
    normalize_parser.add_argument("--output", type=Path, required=True)
    promote_parser = subparsers.add_parser("promote")
    promote_parser.add_argument("fresh", type=Path)
    promote_parser.add_argument("target", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "check-dependencies":
            check_dependencies()
        elif args.command == "normalize":
            print(json.dumps(normalize(args.source, args.output), indent=2))
        elif args.command == "promote":
            result = promote_evidence(args.fresh, args.target)
            print(json.dumps(result, indent=2))
    except (ValueError, RuntimeError) as error:
        parser.error(str(error))
    except OSError as error:
        parser.error("filesystem error: {}".format(error))


if __name__ == "__main__":
    main()
