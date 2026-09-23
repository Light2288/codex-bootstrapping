# Contributing

Contributions are welcome. Please open an issue or pull request describing the
problem and its scope before making a large change.

## Development expectations

- Keep the public plugin provider-neutral and do not add credentials, machine
  configuration, caches, or backups.
- Do not vendor or edit Superpowers; it is a runtime dependency.
- Preserve the profile installer's idempotent, conflict-safe behavior.
- Add focused regression coverage for behavior changes and run the complete
  test suite before submitting a pull request.

The historical migration source is not part of this repository's editable
surface. Changes belong here, not in a live Codex or agent installation.
