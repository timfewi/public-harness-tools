---
name: sui-move
description: Route Sui Move contract, language, framework, review, and learning requests to source-backed local guidance. Use for Move code on Sui; do not use for Aptos Move or general Sui frontend-only work.
---

# Sui Move

Treat Sui Move as its own dialect and object model. Do not import Aptos assumptions such as
`signer`, `move_to`, `borrow_global`, or account-global storage.

Route the request to the narrowest relevant sibling skill:

- Authoring, package setup, tests, debugging, or framework API use: `sui-move-author`.
- Correctness, security, abilities, ownership, or upgrade review: `sui-move-review`.
- Explanations, exercises, or a learning path: `sui-move-learn`.

For version-sensitive syntax or APIs, query the local source snapshot before answering. Resolve the
tool as `move-kb` on `PATH`, or `${SUI_MOVE_KB_ROOT}/bin/move-kb` when that variable is set. Use
`search --json` for machine-readable results and cite the returned source or site URL. If the local
tool is unavailable, say that freshness is unverified and consult the official Sui documentation.

Keep network selection, signing, publishing, upgrading, and transactions separate from code
authoring. Never infer permission to spend funds or mutate an on-chain package.
