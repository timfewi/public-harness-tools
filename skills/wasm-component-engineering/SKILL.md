---
name: wasm-component-engineering
description: Build, inspect, compose, test, and evolve WebAssembly components and WIT contracts with explicit WASI capabilities and compatibility gates. Use for Component Model work; not for general release provenance or arbitrary core-Wasm optimization.
---

# WASM Component Engineering

Produce a valid component whose WIT contract, imports/exports, composition, runtime capabilities, compatibility, and component-specific provenance are explicit and tested. Follow the repository's pinned Component Model and WASI generation; do not force WASIp2 when it targets WASI 0.3 or another declared version.

## Inputs and outputs

Inputs are source language/toolchain, component/WASI target, WIT package/world and version, required imports and exports, dependency components/adapters, host runtime, allowed filesystem/network/environment/clock/random capabilities, supported consumers, compatibility baseline, and build/test commands.

Return the component binary and digest, canonical extracted WIT, import/export inventory, composition graph, capability grant matrix, validation and runtime test results, compatibility verdict with classified interface changes, and component-specific metadata that a general release process can attach to its provenance.

## Workflow

1. Read repository instructions, manifests, lockfiles, WIT files, generated bindings, component metadata, adapters, and pinned versions of wasm-tools, Wasmtime, cargo-component, wit-bindgen, wac/wkg, or language equivalents. Confirm tool availability before choosing commands; use declared typed WASM capabilities when the environment provides them.
2. Name the target precisely: core module or Component Model component, WIT package/world, WASIp1/WASIp2/WASI 0.3, sync/async model, and runtime version. Preview 2, WASI 0.2, and WASIp2 are common names for the same generation, but this is version-sensitive and not a license to silently retarget.
3. Treat WIT as the contract. Inventory package IDs and semantic versions, worlds, interfaces, resources, types, functions, imports, and exports. Generate bindings from the authoritative WIT rather than manually keeping duplicate signatures. Inspect the built binary's embedded WIT and compare it with the source contract.
4. Classify compatibility from consumer impact, not version text alone:
   - changed or removed exports, renamed types/cases/fields, and tighter error/resource behavior are potentially breaking;
   - new required imports expand host obligations and capabilities and are breaking for existing hosts;
   - additive exports may be compatible but still require generated-binding checks;
   - version-qualified and unqualified package/interface names do not automatically match.
   Test representative old consumers and new consumers/hosts against the candidate.
5. Build with the repository's pinned adapter and toolchain, then validate the resulting component. Use wasm-tools validate and wasm-tools component wit, or equivalent declared capabilities, for structural evidence. Record adapter and dependency component digests.
6. Compose imports with dependency exports explicitly. Inspect both sides before composition; interface shape and version must match. After composition, re-extract WIT and confirm which imports remain and which exports are exposed. Composition success alone does not prove runtime behavior.
7. Define a least-capability host matrix. Start from an empty/null context where the runtime supports it, then grant only named preopened directories, environment entries, arguments, clocks/randomness policy, or network access. Do not inherit ambient stdio, environment, filesystem, or network merely for convenience.
8. Run positive tests with the minimum intended grants and negative tests with each sensitive grant removed or narrowed. The component must fail in the expected structured way rather than escaping to ambient authority. Include resource lifecycle, error mapping, encoding, concurrency/async, and cross-language round trips relevant to the contract.
9. Record WASM-specific provenance inputs: component digest, extracted-WIT digest, WIT package/world, target generation, tool/adapter/dependency component versions and digests, composition graph digest, and capability-policy digest. Hand these to release-engineering for the general SBOM, SLSA/in-toto attestation, signing, and publication chain.
10. Publishing WIT/component packages, writing a registry, or invoking remote signing needs exact external authority. Stage and verify locally first.

## Reusable component contract

~~~yaml
schema: wasm-component-contract/v1
target:
  model: component
  wasi: "0.2"
  world: example:service/api@1.2.0
toolchain:
  wasm_tools: repository-pin
  runtime: wasmtime-pinned
build:
  argv: [cargo, component, build, --release, --locked]
artifacts:
  component: target/wasm32-wasip2/release/service.wasm
  extracted_wit: artifacts/service.wit
checks:
  - [wasm-tools, validate, target/wasm32-wasip2/release/service.wasm]
  - [wasm-tools, component, wit, target/wasm32-wasip2/release/service.wasm]
imports:
  expected: [wasi:cli/stdout@0.2.0]
exports:
  expected: [example:service/api@1.2.0]
capabilities:
  filesystem_preopens: []
  network: none
  inherited_environment: []
  inherited_stdio: [stdout]
negative_tests:
  - remove: stdout
    expected: structured-capability-failure
compatibility:
  baseline_wit: compatibility/api-1.1.wit
  old_consumer: pass
  new_consumer: pass
provenance_inputs:
  component_sha256: HEX
  extracted_wit_sha256: HEX
  capability_policy_sha256: HEX
~~~

Adapt target paths and commands to the pinned language toolchain. Never copy the example's WASI version into a project without confirming its target.

## Gates

Positive gates require structural validation, source-versus-extracted WIT agreement, exact import/export inventory, successful composition with no unexpected remaining imports, representative cross-language/runtime tests, minimum-capability success, denied-capability negative tests, and compatibility results against the declared baseline.

Stop when core module/component or WASI generation is ambiguous; generated bindings are stale; WIT versions or shapes do not match; a new import silently expands authority; the runtime inherits ambient capabilities; validation/composition output is missing; negative tests succeed without the denied grant; old consumers fail despite a compatible-version claim; adapter/dependency digests are unknown; or publication/provenance is claimed without release-engineering verification.

## Boundaries

This skill owns WIT, component binaries, composition, WASI generation, capability security, component compatibility, and WASM-specific provenance inputs. release-engineering owns general SBOMs, SLSA/in-toto provenance, attestations, signing, and publication. dependency-maintenance owns dependency selection, while this skill decides whether a WIT/component update is compatible. performance-profiling owns performance experiments.

Primary references: the WIT reference at https://component-model.bytecodealliance.org/design/wit.html, component composition at https://component-model.bytecodealliance.org/composing-and-distributing/composing.html, Component Model packages at https://component-model.bytecodealliance.org/design/packages.html, Wasmtime WASIp2 at https://docs.wasmtime.dev/api/wasmtime_wasi/p2/index.html, and current Component Model version notes at https://component-model.bytecodealliance.org/reference/faq.html.
