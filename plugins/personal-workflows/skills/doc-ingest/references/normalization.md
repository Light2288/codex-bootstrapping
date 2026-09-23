# Deterministic normalization contract

The packaged normalizer is a byte-for-byte migration of:

```text
/Users/davide/.config/opencode/tools/document_ingest.py
```

Migration date: 2026-09-23. OpenCode package metadata is intentionally not
included.

## Inputs and layout

- The source is one real local directory, never a URL or symlink.
- The output is a different, non-symlink, absent-or-empty directory outside
  the source tree.
- Discovery is recursive and deterministic. Relative paths use POSIX
  separators, sort lexicographically, and receive stable `S1`, `S2`, ... IDs.
- Every regular file is inventoried. Unknown extensions are registered as
  unsupported with failed coverage rather than omitted. An empty directory, or
  any batch with no fully readable supported source, is never `COMPLETE`.
- Normalized Markdown is stored under `sources/S<n>/`, extracted assets under
  `intermediates/S<n>/`, and coverage in `extraction-report.json`.
- The source is never modified. Discovered symlinks are recorded and never
  followed.

Supported inputs are text/Markdown, PDF, DOCX, XLSX, PPTX, PNG, JPEG, GIF,
WebP, and safe SVG. Legacy `.doc`, `.xls`, and `.ppt` inputs are registered as
unsupported rather than ignored or converted.

## Safety and fidelity

The script uses Python's standard library for OOXML extraction and does not
execute macros. It rejects duplicate and encrypted archive members. It
validates paths before following relationships or extracting media and rejects
unsafe paths at those boundaries. Inert, unreferenced archive entries that are
neither followed nor extracted may be ignored; the normalizer does not promise
whole-archive member-name rejection. Active or externally referencing SVG is
rejected. External OOXML relationships are never fetched and prevent rendering
while preserving safe structured extraction.

Limits are 10 MiB per direct text source, 100 MiB per direct PDF/image source,
64 MiB per OOXML XML/relationship member, 200 MiB aggregate expanded OOXML
content, and 100,000 cells per XLSX worksheet. Compression-ratio checks protect
large non-XML members. LibreOffice rendering, when locally installed, runs
headlessly with an isolated temporary profile and a 120-second timeout. The
script never installs it.

DOCX preserves referenced media and labels unreferenced package media. XLSX
keeps worksheet-owned cells, formulas, tables, charts, and media; orphan
package items are omitted and reported. PPTX follows declared slide order and
reachable notes/media/charts; filename fallback is used only when the
presentation part is absent and is reported as a limitation.

## Coverage truthfulness

Every registered source includes path, ID, format, method, status, coverage,
normalized reference, assets, and visuals. Successfully processed sources also
include a `warnings` list, which may be empty. Failed, skipped, or unsupported
sources may omit `warnings`; their `reason`, status, coverage, and method carry
the failure or limitation instead. The only valid status/coverage pairs are:

- `COMPLETE` / `COMPLETE`
- `COMPLETE` / `PARTIAL`
- `FAILED` / `FAILED`
- `SKIPPED` / `FAILED`
- `UNSUPPORTED` / `FAILED`

Batch `COMPLETE` requires every source to be fully complete. Any other pair
makes the batch `PARTIAL`. Processing continues after source-local failures so
readable results survive. In particular, a failed or unsupported source has
`FAILED` coverage, a failure or no-extraction method, and a reason, and forces
batch `PARTIAL`.

Direct PDF and image inputs are signature-checked and copied, but this alone
does not inspect or extract their contents into located evidence. They retain
`COMPLETE` processing status with `PARTIAL` coverage and a warning until a
format-aware inspection path supplies that evidence.

Each source writes into an independent temporary staging root. Its artifacts
enter the batch only after all source-local extraction and validation succeeds;
failure removes the staging root before the failed source is reported.

## Promotion

Promotion accepts only real sibling directories on the same filesystem. The
fresh sibling must contain a nonempty `manifest.md`, a valid
`extraction-report.json`, and real in-bound non-symlink artifacts for every
reference. Every other regular file is rejected as unreported residue. Existing
evidence is moved to a unique backup, fresh evidence is renamed into place, and
failures attempt rollback. No merge or silent overwrite is permitted.
