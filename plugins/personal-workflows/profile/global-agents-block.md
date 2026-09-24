<!-- personal-workflows:start -->
## Personal workflow routing

- When a personal adapter and its Superpowers base both apply, use the personal adapter.
- The adapter must load and follow the current Superpowers skill, add only its documented extensions, and never run the base workflow twice.
- If the personal adapter is unavailable, explicitly select and load the applicable skill from the supplied `superpowers:*` catalog. When that skill is present in the catalog, do not claim that it is missing or unavailable.

## Managed model routing

These owned values are the runtime model roles used by `spec-implement`:

- `full`: `gpt-5.6-sol`
- `light`: `gpt-5.6-luna`

Only the marked personal-workflows block may manage these values. A light
request remains subject to the workflow's eligibility and escalation gates.

## Working agreements

- Apply YAGNI and avoid speculative abstractions or single-use wrappers.
- Comments explain intent and tradeoffs, not the next line of code.
- Never swallow errors; handle, contextualize, or rethrow them.
- Remove dead code and follow the nearest project conventions.
- Keep progress updates concise and distinguish verified evidence from inference.
<!-- personal-workflows:end -->
