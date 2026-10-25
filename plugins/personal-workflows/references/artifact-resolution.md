# Artifact Resolution

Use this contract whenever a personal workflow locates or writes a
specification or implementation plan. It preserves legacy artifacts as
read-only inputs while making Superpowers locations the destination for all
new work.

## Inputs and locations

Resolve each artifact kind separately, then validate the specification/plan
pair before writing or implementing.

- New specifications:
  `docs/superpowers/specs/YYYY-MM-DD-<slug>.md`
- New plans: `docs/superpowers/plans/YYYY-MM-DD-<slug>.md`
- Legacy specification: `specs/<slug>.md`
- Legacy plan: `plans/<slug>.md`

New artifacts must include an exact metadata line of the form
`**Slug:** \`<slug>\``. Match that value exactly; do not infer a match from a
similar filename. An explicit user path is a candidate even when older
metadata is absent. Normalize paths relative to the repository root and
reject paths of the wrong artifact kind. If an explicitly selected legacy
`specs/<slug>.md` has no Slug, its exact legacy path supplies the slug; do not
derive identity from a merely similar historical filename.

## Canonical naming

Resolve existing artifacts before choosing a destination. Existing artifacts
keep their filenames and references; never rename them to fit this convention.

- For a newly originated specification, use the specification's original
  creation date as `YYYY-MM-DD` and omit the `-design` suffix. Use the date on
  which its content was first created, including an earlier unsaved draft
  when that date is known, rather than a later approval or save date.
- For a missing plan, use the selected specification's exact basename,
  including historical suffixes. Put it in `docs/superpowers/plans/`, even
  when planning occurs on a later date. Resolve the specification first;
  do not use the planning session's date for its filename.
- Revisions preserve the selected new-path artifact's basename. A revision
  sourced from a legacy location keeps that source basename in the
  corresponding `docs/superpowers/` directory and records provenance; resolve
  any existing destination before writing. The legacy source stays read-only.
- An explicitly requested new destination must satisfy these rules. A
  conflicting requested name is `CONFLICT`; request clarification rather
  than silently renaming, accepting the mismatch, or overwriting a file.

For slug selection:

- Use an explicitly supplied `Slug` when present.
- When no slug is supplied, derive it from the approved topic: lowercase it,
  replace each run of non-alphanumeric characters with one hyphen, trim hyphens
  from both edges, and truncate to 50 characters before trimming any trailing
  hyphen.

If the result is empty, or if more than one topic remains plausible, stop and
ask the user for the exact slug. Never guess among topics or conflicting
sources. Copying the resolved specification's basename is required and is
distinct from ranking candidates by date.

## Document metadata and dates

Newly authored documents include:

- `**Slug:**` with the shared exact slug.
- `**Created:** YYYY-MM-DD` for that document's actual creation date.
- `**Updated:** YYYY-MM-DD` for its latest edit date, initially equal to Created.
- Plans also require `**Spec:**` with an explicit path or Markdown link to the
  selected specification. Plain paths beginning `docs/superpowers/specs/` or
  `specs/` are repository-relative, including backtick-wrapped values in older
  plans. Relative Markdown link destinations and explicit `./` or `../` paths
  resolve from the plan's parent directory; absolute paths are used directly.
  Normalize the result relative to the repository root. If another spelling
  has multiple plausible bases, report `CONFLICT` rather than guessing.

Preserve known Created on revisions and change Updated on edits. Each document
has its own dates: a plan created later has a later Created while its filename
still uses the specification's date. Never invent missing historical dates or
backfill untouched documents. For a newly materialized legacy revision with
no known Created, record the new document's actual creation date and identify
the legacy source in Provenance; this does not assert the source's creation
date. If an original date is necessary but cannot be established, ask rather
than guess.

Contradictory identity metadata or dates are `CONFLICT`. In particular, a new
specification's filename date must agree with its known original Created.
Existing historical filename differences alone do not create a conflict.

## Deterministic lookup

1. Collect new candidates under the relevant `docs/superpowers/` directory
   whose `Slug` metadata exactly matches, plus any explicit user path.
2. Check the exact legacy path for the same slug, plus any explicit legacy
   path.
3. Deduplicate paths. Zero candidates is `MISSING`; a sole new or legacy
   candidate is `NEW_ONLY` or `LEGACY_ONLY`.
4. When new and legacy candidates both exist, compare their bytes and their
   provenance. They are `SAME_SOURCE` when byte-identical or when either
   artifact's `Provenance` metadata explicitly names the other normalized
   path.
5. Any remaining multiple plausible candidates are `CONFLICT`. Do not rank by
   date, location, or apparent completeness. Request the user's selection
   before continuing.

Mentioning a path makes it a candidate; it counts as conflict resolution only
when the user explicitly selects it as the source.

## Pair validation and resuming in another chat

Accept a shared slug or an explicit specification/plan path as the entry point.
For an explicit plan, follow its Spec reference as a specification candidate
before resolving both kinds. Resolve an existing plan before generating a new
plan path so a historical plan with a different basename is reused.

After selecting the specification, find plans by the exact shared Slug and by
explicit Spec references to that normalized specification path. For a selected
metadata-poor historical specification, an unambiguous linked plan can supply
the shared slug. Multiple plausible linked plans remain `CONFLICT`; a Spec
reference does not silently select among duplicate same-slug specifications.

Validate any Slug values and any explicit Spec reference against the selected
pair. A plan pointing to another specification, mismatched Slug values, or
contradictory explicit selections require clarification before writing or
implementing. Older artifacts without Spec metadata remain discoverable by
exact Slug, explicit selection, and provenance; do not invent a link or pair
them by filename similarity. Missing required sources remain `MISSING`.

Report the selected paths and resolution outcomes, then resume at the earliest
unapproved stage. Finding a pair does not establish its approval. No date or
filename needs to be remembered to resume by slug, and historical names need
not match.

## Outcomes

| Outcome | Selected path | Required behavior |
|---|---|---|
| NEW_ONLY | new | Read and, after the governing approval gate, update the new artifact. |
| LEGACY_ONLY | legacy | Read the legacy artifact; write any revision to the canonical new location with provenance. |
| SAME_SOURCE | new | Treat both paths as one source and use the new artifact for subsequent writes. |
| CONFLICT | none | Request the user selection and make no artifact write. |
| MISSING | none | Report the missing source, or create the canonical new artifact when the request is to define it. |

## Write invariants

- Never modify, rename, delete, or overwrite a legacy artifact.
- New artifacts and revisions go only to the canonical Superpowers location.
- A revision sourced from another path records that exact normalized path in
  `Provenance`.
- Do not write on `CONFLICT`. After selection, preserve both candidates and
  apply the legacy-read/new-write rule to the selected source.
