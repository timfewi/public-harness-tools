---
name: test-and-regression
description: Reproduce failures and create deterministic regression tests, fixtures, baselines, oracles, and flaky-test diagnoses with executable pass/fail gates. Use for test behavior; not for CI pipeline topology or implementing unrelated fixes.
---

---
name: test-and-regression
description: Reproduce failures and create deterministic regression tests, fixtures, baselines, oracles, and flaky-test diagnoses with executable pass/fail gates. Use for test behavior; not for CI pipeline topology or implementing unrelated fixes.
---

# Test and Regression

Turn a reported defect or unstable signal into a reproducible, falsifiable test contract. Keep failure reproduction, test design, and implementation repair distinct so a passing test cannot merely encode the current behavior.

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

## Executable reusable gate

When the repository lacks an equivalent repeat gate, materialize this as a temporary helper or a maintained script when requested. It accepts argv directly and keeps one log per run.

~~~sh
#!/bin/sh
set -eu

if [ "$#" -lt 4 ]; then
  echo "usage: regression-gate.sh pass|fail|flake RUNS ARTIFACT_DIR -- COMMAND [ARG ...]" >&2
  exit 64
fi

mode=$1
runs=$2
artifact_dir=$3
shift 3
if [ "${1:-}" != "--" ]; then
  echo "missing -- before command" >&2
  exit 64
fi
shift
case "$mode" in pass|fail|flake) ;; *) echo "invalid mode" >&2; exit 64 ;; esac
case "$runs" in ''|*[!0-9]*) echo "RUNS must be a positive integer" >&2; exit 64 ;; esac
if [ "$runs" -eq 0 ] || [ "$#" -eq 0 ]; then
  echo "RUNS and COMMAND must be non-empty" >&2
  exit 64
fi

mkdir -p "$artifact_dir"
pass_count=0
fail_count=0
i=1
while [ "$i" -le "$runs" ]; do
  if "$@" >"$artifact_dir/run-$i.log" 2>&1; then
    pass_count=$((pass_count + 1))
  else
    fail_count=$((fail_count + 1))
  fi
  i=$((i + 1))
done
printf 'runs=%s pass=%s fail=%s\n' "$runs" "$pass_count" "$fail_count"

case "$mode" in
  pass)  [ "$fail_count" -eq 0 ] ;;
  fail)  [ "$pass_count" -eq 0 ] ;;
  flake) [ "$pass_count" -gt 0 ] && [ "$fail_count" -gt 0 ] ;;
esac
~~~

Use fail mode for a deterministic negative control, pass mode for the repaired behavior, and flake mode only to demonstrate mixed outcomes. Also inspect logs for the expected signature; exit status alone cannot prove the same failure occurred.

## Gates

A positive gate requires an exact reproducible command, controlled fixtures and environment, a reviewed oracle, negative-control failure for the intended reason, positive-control success, stable repeated focused runs, and all applicable wider tests.

Stop as failed or inconclusive when the original defect is not reproduced; the negative control passes; the positive control fails; snapshots changed without semantic review; a retry masks failures; logs show different failure signatures; fixtures depend on mutable external state; teardown leaks resources; only one flaky run was attempted; required environment data is missing; or the broader suite was required but not run.

## Boundaries

This skill owns reproduction, tests, fixtures, oracles, baselines, negative controls, and flake diagnosis. ci-workflows owns runners, matrices, cache, permissions, and pipeline aggregation. performance-profiling owns statistically meaningful timing regressions; this skill may call its benchmark gate but should not turn wall-clock assertions into ordinary unit tests. Dependency or product fixes remain separate unless requested.

Primary reference: pytest's flaky-test guidance at https://docs.pytest.org/en/stable/explanation/flaky.html. Use the repository's test framework documentation for fixture scope, process/thread behavior, seeding, and result formats.
