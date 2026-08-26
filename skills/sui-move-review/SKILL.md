---
name: sui-move-review
description: Review Sui Move packages for correctness, security, object lifecycle, authorization, composability, tests, and upgrade risk. Use when auditing or critiquing .move code and Move package changes.
---

# Sui Move Review

Lead with concrete findings, ordered by impact, and cite file and line locations. Do not rewrite code
unless the user also asks for fixes.

Establish the package edition, compiler/Sui version, dependencies, published IDs, upgrade policy, and
test commands. Query the local corpus for any uncertain framework invariant or signature, for example:

```console
move-kb search --json 'transfer public_transfer store key'
move-kb search --json 'shared object authorization capability'
move-kb search --json 'package upgrade policy compatibility'
```

Check the boundaries that are specific to Sui Move:

- object creation, transfer, sharing, freezing, wrapping, receiving, and deletion;
- ability choices and unintended public transfer or wrapping enabled by `store`;
- authorization based on capabilities, witnesses, ownership, or sender identity;
- shared-object contention, stale assumptions, and unbounded dynamic fields or tables;
- coin/balance conservation, rounding, abort paths, and hot-potato consumption;
- event truthfulness, clock/randomness use, PTB composability, and return-value handling;
- initialization, publication, upgrade compatibility, and privileged capability custody;
- positive, negative, multi-sender, and invariant tests.

Separate confirmed defects from design tradeoffs and unresolved questions. Never treat a passing
build as proof of economic or authorization safety, and never publish or execute transactions during
a review.
