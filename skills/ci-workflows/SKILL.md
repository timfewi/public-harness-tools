---
name: ci-workflows
description: Design, refactor, and verify CI pipeline execution contracts, permissions, matrices, caches, artifacts, and failure semantics across providers. Use for pipeline and runner behavior, including CI-only environment or scheduling failures; not for release contents or regression-test, fixture, and oracle design.
---

# CI Workflows

Turn repository commands into a least-privilege, reproducible pipeline with explicit job contracts. Preserve the repository's chosen CI provider and declared toolchain unless the user requests a migration.

## Inputs and outputs

Inputs are repository instructions, current workflow files, event and trust model, required checks, platform/toolchain matrix, available runners, secrets or federated identities, cache policy, artifact consumers, and provider limits.

Output the changed workflow plus a compact contract for each job: triggers, trusted and untrusted inputs, permissions, environment, argv, dependencies, produced reports/artifacts, timeout, retry policy, and success/failure semantics. Report provider validation and the underlying commands that actually ran.

## Workflow

1. Inspect current workflows, local task runners, lockfiles, toolchain pins, branch protection expectations, and available execution capabilities. Reuse the same formatter, linter, build, and test entry points locally and in CI rather than duplicating logic in provider YAML.
2. Classify every trigger. Treat pull requests from forks and dependency automation as untrusted. Map each job's required token scopes, secrets, network access, write targets, and runner isolation. Untrusted code must not run with write tokens or production secrets.
3. Express a provider-neutral job DAG before editing YAML. Split jobs where trust, environment, outputs, or failure policy differ; do not split merely for visual neatness. Make required dependencies explicit and ensure skipped upstream jobs cannot turn a required downstream gate green.
4. Pin the execution environment: runner image or container digest where supported, language/toolchain version, dependency lockfile, and third-party action/workflow commit. A movable tag is not equivalent to a full immutable commit. Prefer short-lived OIDC credentials over long-lived cloud secrets when the provider and target support it.
5. Treat caches as untrusted optimization. Keys must cover OS/architecture, toolchain, dependency manifests/locks, and relevant build mode. Cache restore must not be required for correctness. Separate cache writes from untrusted contexts when poisoning is possible, and verify a clean-cache run.
6. Build the smallest meaningful matrix. State which axes are required, experimental, or allowed to fail. Use concurrency cancellation for replaceable validation runs, but do not cancel stateful deployment or publication work without an explicit idempotency design.
7. Give every job machine-readable outputs: exit status plus JUnit, coverage, SARIF, benchmark, package, or log artifacts as appropriate. Define retention and consumers. Ensure artifact names are unique across matrix cells and that upload steps still run for diagnostic failures when safe.
8. Validate provider syntax and expressions, then run the underlying commands in the declared isolated environment. Exercise at least one expected-success path and relevant negative paths. Triggering a hosted run or changing branch rules is an external mutation and needs its own authority.
9. After an authorized hosted run, inspect every required matrix cell, skipped/cancelled state, artifact, and annotation. A green aggregate is insufficient if required jobs never ran.

## Reusable provider-neutral contract

Write this before provider-specific configuration and keep command values as argv:

~~~yaml
schema: ci-job-contract/v1
job: unit-tests
triggers: [pull_request, push]
trust: untrusted-code
needs: [lint]
permissions:
  repository_contents: read
  id_token: none
environment:
  runner: ubuntu-pinned
  toolchain: from-repository-pin
command: [project-task, test, --locked]
matrix:
  required:
    os: [linux]
    runtime: ["3.12", "3.13"]
cache:
  paths: [package-manager-cache]
  key_inputs: [os, architecture, toolchain, lockfile-sha256]
outputs:
  - {name: junit, path: artifacts/junit.xml, when: always}
timeout_minutes: 20
retries: 0
success:
  require_all_matrix_cells: true
  require_artifacts: [junit]
~~~

Translate the contract into the existing provider's syntax; keep the contract in project documentation only when it will be maintained and reused.

## Gates

Positive gates require provider syntax validation, successful execution of the actual job commands from a clean environment, all required matrix cells and dependency edges, expected reports/artifacts, least-privilege permissions, immutable third-party references where supported, and a cache-miss path that still passes.

Negative gates must demonstrate that malformed configuration fails validation; a failing command fails the required check; a missing required artifact is observable; untrusted triggers cannot access secrets or write tokens; an omitted/failed upstream job cannot yield a false success; and cancellation or retry cannot duplicate stateful work. Stop as incomplete when hosted execution was required but not authorized or observable.

## Boundaries

This skill owns pipeline topology, triggers, runners, permissions, caches, matrices, concurrency, and job/artifact contracts. test-and-regression owns test oracles, fixtures, baselines, and flaky-test diagnosis. release-engineering owns versions, releasable subjects, SBOM/provenance contents, signing, and publication. dependency-maintenance owns dependency selection; this skill only schedules its checks.

Primary references: GitHub Actions secure-use guidance at https://docs.github.com/en/actions/reference/security/secure-use, workflow syntax at https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax, concurrency at https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency, and dependency caching at https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching. Apply equivalent official guidance for the repository's actual provider.
