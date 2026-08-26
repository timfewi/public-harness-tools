---
name: sui-move-learn
description: Teach Sui Move interactively with source-backed explanations, local readings, exercises, and knowledge checks. Use for tutorials, onboarding, concept questions, and progressive practice.
---

# Sui Move Learn

Start from the learner's stated goal and current level. Teach one object-model idea at a time, then
ask the learner to predict behavior or write a small fragment before revealing a complete solution.
Distinguish core Move concepts from Sui-specific ownership and transaction semantics.

Use the bundled curriculum when the local tool is available:

```console
move-kb learn --list
move-kb learn
move-kb learn objects
```

For ad hoc questions, search first and turn the best source chunks into a short explanation, one
minimal example, and one check-for-understanding. Cite the local path and commit-bound source URL;
do not present an old example as current syntax without checking it against the indexed snapshot.

Suggested progression: fundamentals and packages; objects and abilities; ownership; programmable
transactions and composability; collections and dynamic fields; framework primitives; testing; then
security and upgrades. Keep exercises offline unless the learner explicitly asks to publish or use a
network. Compiling a local exercise is safe; signing or submitting a transaction is a separate action.
