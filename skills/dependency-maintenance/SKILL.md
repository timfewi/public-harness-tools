---
name: dependency-maintenance
description: Inventory, assess, update, and verify project dependencies and lockfiles with minimal compatible change sets. Use for routine, security, license, or support-window maintenance; not for CI topology or publishing releases.
---

# Dependency Maintenance

Produce the smallest justified dependency change set with a reproducible resolution record and evidence that compatibility, security, licensing, and lockfile state were evaluated. Do not equate newest with safest or compatible.

## Inputs and outputs

Inputs are repository instructions, manifests and lockfiles, workspace/package boundaries, pinned toolchains and registries, support policy, update goal, allowed version range, vulnerability and license policy, network/offline constraints, and verification commands.

Return a dependency inventory, assessment findings with source and timestamp, selected update set with rationale, exact manifest/lockfile/source diff, resolver argv and environment, verification evidence, remaining advisories or policy exceptions, and rollback instructions.

## Workflow

1. Discover every first-party manifest, lockfile, vendored set, generated dependency file, CI action, container base, toolchain pin, and package workspace. Identify the authoritative resolver for each ecosystem. Do not edit generated files by hand when the ecosystem tool owns them.
2. Capture a baseline from the current lock state: clean install or offline resolution when supported, existing tests, dependency graph, duplicate versions, outdated direct dependencies, known vulnerabilities, licenses, and unsupported runtimes. Separate direct, transitive, build, development, and runtime dependencies.
3. Classify the goal: minimal security remediation, support-window migration, routine patch/minor refresh, deliberate major upgrade, license remediation, or lockfile repair. Confirm affected versions and fixed ranges from authoritative advisories and upstream release/migration notes. A scanner hit is a lead; reachability, exploitability, and policy still need explicit assessment.
4. Select tools from repository evidence. Prefer the pinned ecosystem manager with immutable/locked flags for resolution, tree inspection, and update. Use OSV-Scanner for supported source/lockfile vulnerability discovery and the repository's established license scanner or SPDX data for license evidence. If required tools or offline indexes are unavailable, report an environment blocker instead of fabricating freshness.
5. Plan a minimal update set. Keep unrelated locks stable, respect compatibility ranges, and include coupled packages only when the resolver or upstream contract requires them. Major upgrades, transitive overrides, abandoned-package replacement, and license changes need their own migration rationale.
6. Execute resolution only in the declared isolated repository environment. Automated remediation commands may execute package-manager scripts or contact configured registries; do not run them on untrusted source or with credentials. Prefer explicit package/version selection over broad update-all operations.
7. Review the full diff. Explain every manifest change, lockfile package/version/checksum/source change, added or removed transitive dependency, generated file, and required source/config migration. Unexpected registry, Git URL, checksum disappearance, lifecycle script, or broad graph churn is a stop signal.
8. Verify in layers: immutable/offline install if feasible, resolver consistency, compilation/type checking, focused tests for changed integration points, full applicable tests, static/license/vulnerability scans, and the project's packaging or runtime smoke test. Re-scan the resulting lock state rather than the requested version.
9. Record unresolved findings and rollback. Reverting manifest and lockfile together must restore the baseline. Do not claim a vulnerability fixed when the selected artifact remains affected or the scanner data was unavailable.

## Reusable update record

~~~yaml
schema: dependency-update/v1
goal: minimal-security-remediation
environment:
  toolchain: repository-pin
  registry_mode: offline-or-approved
baseline:
  manifests: [path/to/manifest]
  lockfiles: [path/to/lockfile]
  graph_digest: SHA256
selection:
  - package: example
    from: 1.2.3
    to: 1.2.7
    direct: true
    reason: OSV-ID-or-support-policy
    fixed_range_source: ADVISORY_URI
resolver:
  argv: [package-manager, update, example, --precise, 1.2.7]
diff_limits:
  unrelated_direct_changes: 0
verification:
  immutable_install: pass
  build: pass
  focused_tests: pass
  full_tests: pass
  vulnerability_scan: pass
  license_scan: pass
remaining_findings: []
rollback:
  files: [path/to/manifest, path/to/lockfile]
~~~

## Gates

A positive gate requires a reproducible baseline, authoritative reason for each selected change, ecosystem-native lock consistency, explained graph diff, successful immutable install/build/applicable tests, and post-update vulnerability/license results with any exceptions named.

Fail or stop when manifests and lockfiles disagree; the resolver changes unrelated direct dependencies without justification; a source changes registry or loses integrity metadata unexpectedly; required indexes are stale/unavailable; an advisory's affected range is uncertain; new license terms violate policy; install scripts or credentials would execute in an untrusted context; a major migration is hidden inside routine maintenance; tests are skipped; or rollback cannot restore the prior graph.

## Boundaries

This skill owns dependency inventory, update selection, resolution, lockfiles, advisories, licenses, and update verification. ci-workflows owns scheduling and permissions for automated checks. test-and-regression owns new regression oracles and flaky-test diagnosis. release-engineering owns release artifacts, general SBOM/provenance, and publication. wasm-component-engineering owns WIT/component compatibility even when a component dependency changes.

Primary references: OSV-Scanner project source scanning at https://google.github.io/osv-scanner/usage/scan-source, its remediation safety warning at https://google.github.io/osv-scanner/usage/, Cargo update behavior at https://doc.rust-lang.org/cargo/commands/cargo-update.html, and the current npm audit documentation at https://docs.npmjs.com/cli/commands/npm-audit/. Always use official documentation for the repository's pinned ecosystem-manager version.
