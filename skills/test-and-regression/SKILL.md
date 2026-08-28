---
name: test-and-regression
description: Reproduce failures and design regression tests, fixtures, baselines, oracles, negative controls, flaky-test diagnoses, and reusable regression gates. Use for failure reproduction and test-design work, including CI-only flakes; not for routine test execution after ordinary changes, CI pipeline topology, or product fixes.
---

# Test and Regression

Turn a reported defect or unstable signal into a reproducible, falsifiable test contract. Keep failure reproduction, test design, and implementation repair distinct so a passing test cannot merely encode the current behavior.

## Route before loading context

Select this skill for failure reproduction or minimization, regression-test and baseline design, independent pass/fail oracles, controlled fixtures, negative and positive controls, or flaky-test diagnosis. Decline it for a single straightforward assertion explanation that does not need broader test design, and for merely choosing or running checks after an implementation change; the repository's normal verification workflow owns the latter.

Route ownership explicitly at neighboring boundaries:

- `ci-workflows` owns runner scheduling, matrices, permissions, caches, and pipeline aggregation. When a test flakes only on one runner, use this skill for the reproducer, controlled environment, oracle, and fixture, and co-route CI-specific scheduling or runner changes to `ci-workflows`.
- `performance-profiling` owns repeated latency, throughput, allocation, and statistical regression measurement. For an optimization, use this skill only for the functional correctness oracle and co-route the measurement gate to `performance-profiling`.
- Dependency selection and product repair stay separate unless the request explicitly includes them.

Start with repository instructions, existing test conventions, focused source/test reads, and the smallest executable test command. Load framework documentation only when pinned version behavior affects fixtures, concurrency, or result interpretation. Stop rather than broaden scope when the requested work belongs entirely to a neighboring skill.

## Inputs and outputs

Inputs are the failure report, exact test target, known-good and known-bad behavior when available, repository test commands, environment and dependency pins, fixtures/data, random seeds, clocks/time zones/locales, concurrency settings, and acceptable runtime.

Return:

- a minimal reproduction command and captured environment;
- the observed failure signature and classification as deterministic regression, flaky, environment-specific, or not reproduced;
- a regression test with an explicit oracle and controlled fixtures;
- negative-control evidence that the test detects the bad behavior;
- positive-control evidence that it accepts the intended behavior;
- repeat-run evidence for stability;
- diagnostic artifacts and any unresolved uncertainty.

Do not implement the product fix unless the request includes it.

## Workflow

1. Read repository instructions and existing test conventions. Capture the exact revision, toolchain, lock state, OS/architecture, environment variables relevant to behavior, seed, locale, time zone, service versions, concurrency, and original argv. Redact secrets rather than embedding them in fixtures or logs.
2. Reproduce the smallest failing scope before editing. Preserve stdout, stderr, exit status, crash/timeout details, and a stable failure signature. If it does not reproduce, vary one evidence-backed dimension at a time; report not reproduced rather than guessing.
3. Classify the signal. A deterministic failure repeats under controlled inputs. A flaky test produces both pass and fail outcomes without an intended input change. An environment failure follows a documented environment delta. Retries may diagnose a flake but must not convert it into a green required gate.
4. Define the oracle independently of the implementation. Prefer observable output, state transition, protocol response, invariant, or structured error over internal call counts. Snapshot/baseline updates require semantic review; do not accept a bulk rewrite simply because the tool generated it.
5. Build the smallest realistic fixture. Control clock, randomness, temporary paths, ports, network, process lifecycle, ordering, and shared state as needed. Make setup and teardown idempotent. Avoid production credentials and mutable external services; use approved local fakes or recorded data with provenance.
6. Add a negative control. Run the new test against a known-bad implementation, injected defect, or fixture that represents the defect and confirm the expected failure signature. Use an isolated copy/worktree when changing revisions; never discard user changes to manufacture this proof.
7. Run the positive control against the intended implementation, then the focused test repeatedly and the applicable wider suite. Exercise serial/parallel and order variation only where they test a plausible dependency. Preserve failure logs for every repeat.
8. For flakiness, form hypotheses from the evidence: order leakage, incomplete teardown, clock/timing, seed/randomness, port/filesystem collision, thread/process lifetime, resource exhaustion, or external service variance. Change one variable per experiment and report pass/fail counts; do not quarantine or add retries unless the user requests a temporary mitigation.
9. State exactly what the test proves and what it does not. A passing focused test does not prove the full suite, other platforms, or absence of related regressions.

## Bundled regression gate

When the repository lacks an equivalent repeat gate, run the bundled `scripts/regression-gate.sh` with argv after `--`; it never uses `eval`:

~~~sh
skills/test-and-regression/scripts/regression-gate.sh pass 10 artifacts/regression-positive -- project-test focused-case
skills/test-and-regression/scripts/regression-gate.sh fail 5 artifacts/regression-negative --expect 'expected error code' -- project-test negative-control
skills/test-and-regression/scripts/regression-gate.sh flake 20 artifacts/flake-evidence --expect 'intermittent signature' -- project-test unstable-case
~~~

The mode is an expected classification:

- `pass` succeeds only when every run passes.
- `fail` succeeds only when every run fails and, when `--expect` is supplied, every failure log contains that fixed signature.
- `flake` succeeds only when both pass and fail outcomes occur and every failure has the requested signature. This is diagnostic evidence of instability, never a green required product gate.

`RUNS` must be between 1 and 1000. `ARTIFACT_DIR` must be a new dedicated directory whose parent already exists; the runner rejects dot traversal, symbolic-link parents, and existing output paths. It preserves the command argv exactly in NUL-delimited `command.argv0`, writes one log and exit-status file per run, and records all-pass, all-fail, or mixed classification in `summary.txt`. In pass mode, any nonzero run keeps the gate nonzero; retries never convert required success into green. Review the preserved logs and signature result before accepting a gate.

## Gates

A positive gate requires an exact reproducible command, controlled fixtures and environment, a reviewed oracle, negative-control failure for the intended reason, positive-control success, stable repeated focused runs, and all applicable wider tests.

Stop as failed or inconclusive when the original defect is not reproduced; the negative control passes; the positive control fails; snapshots changed without semantic review; a retry masks failures; logs show different failure signatures; fixtures depend on mutable external state; teardown leaks resources; only one flaky run was attempted; required environment data is missing; or the broader suite was required but not run.

## Boundaries

This skill owns reproduction, tests, fixtures, oracles, baselines, negative controls, and flake diagnosis. ci-workflows owns runners, matrices, cache, permissions, and pipeline aggregation. performance-profiling owns statistically meaningful timing regressions; this skill may call its benchmark gate but should not turn wall-clock assertions into ordinary unit tests. Dependency or product fixes remain separate unless requested.

Primary reference: pytest's flaky-test guidance at https://docs.pytest.org/en/stable/explanation/flaky.html. Use the repository's test framework documentation for fixture scope, process/thread behavior, seeding, and result formats.
