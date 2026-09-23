# Artifact Resolution

Use this contract whenever a personal workflow locates or writes a
specification or implementation plan. It preserves legacy artifacts as
read-only inputs while making Superpowers locations the destination for all
new work.

## Inputs and locations

Resolve one artifact kind and slug at a time.

- New specifications:
  `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
- New plans: `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`
- Legacy specification: `specs/<slug>.md`
- Legacy plan: `plans/<slug>.md`

New artifacts must include an exact metadata line of the form
`**Slug:** \`<slug>\``. Match that value exactly; do not infer a match from a
similar filename. An explicit user path is a candidate even when older
metadata is absent. Normalize paths relative to the repository root and
reject paths of the wrong artifact kind.

## Canonical naming

An explicit valid new-path user path is authoritative for naming. An explicit
legacy path remains only a source candidate under the write invariants below.
Otherwise:

- Use the current session date as `YYYY-MM-DD`.
- Use an explicitly supplied `Slug` when present.
- When no slug is supplied, derive it from the approved topic: lowercase it,
  replace each run of non-alphanumeric characters with one hyphen, trim hyphens
  from both edges, and truncate to 50 characters before trimming any trailing
  hyphen.

Use the result in the location pattern for the artifact kind above.

If the result is empty, or if more than one topic remains plausible, stop and
ask the user for the exact slug. Never choose a date from existing artifacts
or guess among topics.

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
