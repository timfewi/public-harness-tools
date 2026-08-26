---
name: sui-move-author
description: Write, test, debug, and explain Sui Move packages using the current Sui object model and framework APIs. Use for Move.toml, .move files, compiler failures, unit tests, and contract design on Sui.
---

# Sui Move Author

Inspect the target repository's instructions, `Move.toml`, edition, dependency pins, and available
Sui CLI before editing. Preserve the package's established syntax unless the user requests a
migration.

Before relying on a framework function or version-sensitive rule, run a focused local query such as:

```console
move-kb search --json 'dynamic_field borrow_mut'
move-kb search --json 'Move.toml edition package dependencies'
```

Prefer the checked-in framework source and generated framework reference over remembered signatures.
Use the result's commit-bound GitHub URL when citing behavior.

Model assets explicitly:

- Choose `key`, `store`, `copy`, and `drop` from required lifecycle behavior, not convenience.
- Keep `UID` creation and deletion balanced and make ownership transitions visible.
- Return values from composable public functions; add transfer-oriented entry wrappers only when the
  product flow needs them.
- Use capabilities or other explicit authority objects for privileged operations when appropriate.
- Bound collections and shared-object contention when the design could grow without limit.

Run the repository's own formatter, `sui move build`, and focused tests after changes. Compiler and
test output outrank examples from the knowledge base. Publishing, upgrading, signing, or submitting
a transaction requires separate user authorization.
