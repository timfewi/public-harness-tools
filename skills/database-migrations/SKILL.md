---
name: database-migrations
description: Plan, implement, rehearse, and verify schema and data migrations with compatibility, lock, backfill, rollout, and recovery gates. Use for durable database changes; not for ordinary query tuning or application-only refactors.
---

# Database Migrations

Produce a migration that is compatible with the real database engine, current data, deployed application versions, and operational limits. Prefer a recoverable expand-migrate-contract sequence over a one-shot destructive change when old and new application versions can overlap.

## Inputs and outputs

Inputs are engine and exact version, topology and replicas, schema history, migration framework and conventions, current schema/data profile, application deployment order, traffic/load characteristics, availability and lock budgets, backup/recovery evidence, and desired final invariant.

Return a phase plan, migration files, backfill or verification commands, compatibility matrix, estimated locks/rewrites and runtime, rehearsal evidence, rollout and observation plan, rollback or roll-forward plan, and post-migration invariant results.

## Workflow

1. Read repository and database instructions, migration history, schema dump, ORM/model definitions, deployment configuration, and pinned engine/tool versions. Compare migration history with the target database before editing; unresolved drift is a stop condition.
2. State the initial and final invariants and list every application version that may run during the rollout. Inventory dependent indexes, constraints, triggers, views, foreign keys, generated columns, jobs, replicas, CDC/ETL consumers, and permissions.
3. Inspect real data shape with read-only, bounded queries: row counts, nulls, duplicates, invalid values, key distribution, table/index size, and write rate. Do not copy sensitive rows into logs or fixtures when aggregates suffice.
4. Decompose the rollout:
   - Expand: add compatible nullable columns/tables/indexes or non-enforced constraints.
   - Migrate: dual-read/write only when needed, backfill in resumable bounded batches, and verify old/new equivalence.
   - Contract: stop old writes, prove no old application/consumer depends on legacy shape, enforce final constraints, then remove old schema in a later release.
5. For each DDL/DML statement, use the exact engine-version documentation to identify transaction behavior, table rewrite, lock mode/duration, replication impact, disk/WAL growth, timeout, and cancellation semantics. Similar SQL can behave differently across engines and versions.
6. Make backfills idempotent and restartable. Define stable batching keys, batch size, rate limit, checkpoint, retry policy, affected-row expectations, and completion query. Avoid one unbounded transaction. Treat zero or unexpectedly high affected rows as evidence to investigate, not automatic success.
7. Rehearse from a production-like sanitized snapshot or measured staging dataset. Validate migration checksums/naming, generate and review dry-run SQL when the tool supports it, run concurrent old/new application smoke tests, exercise interruption/resume, and measure locks, runtime, replica lag, and resource growth.
8. Define rollout guardrails before applying: maintenance/deployment order, lock and statement timeouts, dashboards/queries, alert thresholds, abort point, and responsible operator. Applying to a live database, changing traffic, or restoring a backup requires explicit authority for that target.
9. After each phase, verify schema history and checksums, database invariants, row counts/checksums or sampled equivalence, constraint validity, old/new application compatibility, error rate, latency, lock waits, and replica/CDC health. Do not start contract until legacy reads/writes are observably absent.
10. Prefer roll-forward after irreversible data transformation. A rollback claim is valid only if rehearsed and data written after cutover can be preserved. Backup existence without a tested restore time is not a rollback plan.

## Reusable migration plan

~~~yaml
schema: database-migration-plan/v1
engine: postgresql
engine_version: "18"
migration_id: 20260828_add_new_field
initial_invariant: legacy_field is authoritative
final_invariant: new_field is non-null and authoritative
compatibility:
  old_app_with_expanded_schema: pass
  new_app_before_backfill_complete: pass
phases:
  - name: expand
    files: [V101__add_new_field.sql]
    expected_lock: ACCESS_EXCLUSIVE-short
    table_rewrite: false
  - name: migrate
    argv: [app-maintenance, backfill, --batch-size, "1000", --resume]
    checkpoint: migration_checkpoints/20260828
    completion_query: SELECT count(*) FROM target WHERE new_field IS NULL
    expected_completion_value: 0
  - name: contract
    prerequisites: [old_write_rate_is_zero, equivalence_gate_passed]
    files: [V102__enforce_and_drop_legacy.sql]
budgets:
  lock_wait_seconds: 2
  statement_seconds: 30
  replica_lag_seconds: 10
recovery:
  preferred: roll-forward
  last_rehearsed_restore: 2026-08-20
~~~

Adapt lock names and semantics to the actual engine; the example is not a portable SQL guarantee.

## Gates

Positive gates require no unexplained drift, old/new compatibility through overlapping phases, reviewed dry-run SQL, production-scale rehearsal or defensible measurements, bounded resumable backfill, explicit lock/runtime/resource budgets, post-phase invariants, and a rehearsed recovery path.

Stop when engine/version is unknown; migration checksums changed after application; destructive contract precedes observed consumer migration; DDL requires an unbudgeted rewrite or blocking lock; data violates a new constraint; the backfill is not idempotent; affected rows or replication lag exceed limits; dry-run differs from applied configuration; rollback would lose post-cutover writes; backup restore is untested; or live authority/observability is absent.

## Boundaries

This skill owns schema history, DDL, data backfills, rollout compatibility, locks, recovery, and database invariants. performance-profiling owns application or query performance experiments beyond migration budgets. ci-workflows may run migration checks but does not define live rollout. release-engineering may package migration files but does not authorize applying them.

Primary references: PostgreSQL 18 ALTER TABLE behavior at https://www.postgresql.org/docs/18/sql-altertable.html, PostgreSQL 18 locking at https://www.postgresql.org/docs/18/explicit-locking.html, Flyway validation at https://documentation.red-gate.com/flyway/reference/commands/validate, Flyway dry runs at https://documentation.red-gate.com/flyway/reference/tutorials/tutorial-dry-runs, and Prisma's expand-contract example at https://www.prisma.io/docs/guides/database/data-migration. Use the actual engine and migration-tool version as authority.
