---
name: release-engineering
description: Build, verify, stage, and publish software releases with versions, release notes, reproducible artifacts, SBOMs, provenance, attestations, and signatures. Use for end-to-end releases; not for CI runner design or WASM interface and capability work.
---

---
name: release-engineering
description: Build, verify, stage, and publish software releases with versions, release notes, reproducible artifacts, SBOMs, provenance, attestations, and signatures. Use for end-to-end releases; not for CI runner design or WASM interface and capability work.
---

# Release Engineering

Produce a release evidence bundle whose artifacts can be traced to one source state and independently verified. Treat staging and publication as separate outcomes: permission to prepare a release does not authorize tags, registry uploads, hosted releases, signing-service calls, or other external mutations.

## Inputs and outputs

Required inputs are the target repository, intended release or version policy, target platforms, declared build environment, required verification commands, artifact formats, and publication target. Resolve missing values from repository instructions and release configuration; ask only when a missing choice changes compatibility or publication.

Return:

- the resolved version and exact source revision, including whether tracked or untracked changes affected the build;
- release notes tied to the actual change range;
- an artifact inventory with media type, size, and cryptographic digest;
- a validated SBOM for each releasable subject when the project supports one;
- provenance or attestation records that bind subjects to source, builder, parameters, and resolved inputs;
- signature and independent verification results when signing is required;
- a staged or published target, plus explicit evidence of which state was reached.

## Workflow

1. Read repository instructions, manifests, version files, tags, release configuration, changelog conventions, and pinned toolchain. Preserve the project's version scheme. Do not infer semantic versioning when the project uses another policy.
2. Define the release contract before building: source revision, artifact names, platform matrix, build argv, environment identity, expected checks, SBOM format, provenance predicate, signer identity policy, and publication target. Record version-sensitive tool behavior from official documentation.
3. Establish a clean build input without discarding user changes. If the working tree is dirty, either use an approved isolated checkout/worktree or state exactly which changes enter the build. Fetching dependencies, running build scripts, or executing repository code belongs in the declared isolated execution environment.
4. Run the repository's release checks and build with its pinned commands. If reproducibility is claimed, build the same source twice in independent clean directories and compare digests. A single successful build proves buildability, not reproducibility. Explain any normalized nondeterminism.
5. Inventory only final subjects. Generate the SBOM from the final build context or artifact, validate its declared SPDX or CycloneDX format, and check that its identity/version correspond to the subject. Generate SLSA/in-toto provenance from the trusted build path where possible; do not present a locally handwritten predicate as platform-authenticated provenance.
6. Sign or attest only with the user's selected identity and authorized service. Verify from a fresh consumer view using expected issuer/identity, subject digest, predicate type, builder, source revision, and external parameters. Missing attestations, unexpected fields, or identity mismatches fail closed.
7. Assemble a staging bundle before mutation. Review version, release notes, digests, artifact set, SBOM, provenance, verification logs, and target coordinates together. Run provider dry-run or local package validation when available.
8. Publish only after exact target and authority are present. Avoid ambiguous latest targets and duplicate retries. Read the resulting registry or hosted release back and compare its digest, version, attachments, and attestations with the staged bundle.

## Reusable release evidence template

Create one record per release and keep argv values as arrays rather than shell strings:

~~~yaml
schema: release-evidence/v1
version: 1.2.3
source:
  repository: REPOSITORY_URI
  revision: FULL_COMMIT_ID
  dirty: false
build:
  environment: pinned-image-or-nix-derivation
  argv: [tool, build, --release]
  reproducibility:
    runs: 2
    equal_subject_digests: true
subjects:
  - path: dist/package.tar.gz
    media_type: application/gzip
    sha256: HEX_DIGEST
sbom:
  format: SPDX-3.0.1
  path: dist/package.spdx.json
  validated: true
provenance:
  predicate_type: https://slsa.dev/provenance/v1
  path: dist/package.intoto.jsonl
verification:
  expected_builder: BUILDER_ID_URI
  expected_issuer: ISSUER_URI
  expected_identity: release-workflow
  result: pass
publication:
  target: registry/package@1.2.3
  state: staged
  authorization_observed: false
~~~

## Gates

A positive release gate requires all requested checks to pass, every advertised artifact to have a digest, the staged subjects to match SBOM/provenance/signature subjects, independent verification to pass, and the published bytes to match the staged bytes when publication occurred.

Stop with a failed or incomplete result when the source state is ambiguous, required artifacts are missing, a check was skipped, reproducibility differs, the SBOM is malformed or names another subject, provenance omits material external inputs, a signature is valid for the wrong identity, a verifier cannot find an expected attestation, credentials or publication authority are absent, the remote version already exists with different bytes, or the published target cannot be read back. Never relabel an inconclusive gate as success.

## Boundaries

This skill owns release contents, general SBOMs, general provenance, signing, verification, staging, and publication. Use ci-workflows for pipeline topology, runner isolation, caching, and job permissions. Use dependency-maintenance for selecting dependency updates. Use wasm-component-engineering for WIT compatibility, component composition, WASI capabilities, and WASM-specific subject inspection; it may add component metadata but must not duplicate the general release chain.

Primary references: SLSA Provenance v1.1 at https://slsa.dev/spec/v1.1/provenance, SLSA artifact verification at https://slsa.dev/spec/v1.1/verifying-artifacts, SPDX 3.0.1 at https://spdx.github.io/spdx-spec/v3.0.1/, and Sigstore in-toto attestation verification at https://docs.sigstore.dev/cosign/verifying/attestation/.
