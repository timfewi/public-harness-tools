---
name: performance-profiling
description: Measure, profile, optimize, and regression-gate software performance with controlled environments and statistically defensible baselines. Use for CPU, latency, throughput, allocation, I/O, or memory work; not for functional test design.
---

# Performance Profiling

Turn a performance concern into a measured comparison that preserves functional behavior. Optimize against a declared workload and budget; do not treat one timing, a profiler screenshot, or a faster noisy run as proof.

## Inputs and outputs

Inputs are the user-visible performance question, representative workload and data, correctness oracle, target metric and percentile, resource limits, baseline revision, candidate revision, environment/toolchain pins, warmup and repetition policy, allowed profiling capabilities, and regression budget.

Return raw machine-readable measurements, environment fingerprint, summary statistics and variability, profiles/traces with collection settings, ranked evidence-backed bottlenecks, one-change-at-a-time comparison, correctness/equivalence results, budget verdict, and uncertainty.

## Workflow

1. Define the claim before measuring: workload, population or request shape, metric, unit, aggregation/percentile, direction, baseline, candidate, minimum meaningful effect, and regression budget. Separate latency, throughput, CPU time, allocation, peak memory, I/O, startup, and binary size.
2. Pin or record source revision, build mode, compiler/runtime, dependencies, machine/VM, CPU topology and frequency policy, memory, kernel/OS, background load, input data digest, affinity, environment, and profiler overhead. If the environment cannot be controlled, widen uncertainty and allow an inconclusive result.
3. Prove functional equivalence with the repository's tests or a workload-specific oracle before comparing performance. A faster wrong result fails.
4. Run a smoke/dry benchmark, then warmups and multiple measured repetitions. Randomly interleave or alternate baseline and candidate when supported to reduce drift. Retain every observation; do not delete outliers without a predeclared rule and explanation.
5. Check noise before profiling. Report median or another appropriate center, dispersion/interval, sample count, and raw values. If normal run-to-run variance overlaps the budget, increase evidence or report inconclusive rather than picking the favorable statistic.
6. Select the profiler that answers the hypothesis:
   - sampling CPU profiler for where on-CPU time accumulates;
   - tracing for latency across threads/processes and waits;
   - allocation/heap profiler for churn, leaks, and peak memory;
   - system counters for cache, branch, page-fault, scheduling, or I/O hypotheses.
   Use repository-declared tools first. On Linux, perf stat/record/report may be appropriate, but performance counters and data files can expose sensitive data; do not escalate privileges or broaden process/system scope without authority.
7. Form a ranked hypothesis from profiles, then change one dominant cause at a time. Keep algorithmic, compiler, cache, I/O, allocation, and concurrency effects distinguishable. Re-run correctness and the same benchmark protocol after each candidate.
8. Compare both practical and statistical significance. Report improvement/regression as an effect with uncertainty, not only a percentage. Check secondary metrics and representative workloads so an average win does not hide tail-latency, memory, or worst-case regressions.
9. Add a durable regression gate only when the runner noise is below the budget. Otherwise store a benchmark and dashboard/manual comparison rather than a brittle hard threshold.

## Reusable performance contract

~~~json
{
  "schema": "performance-gate/v1",
  "workload": {
    "argv": ["bench-tool", "--case", "representative"],
    "input_digest": "sha256:HEX",
    "correctness_argv": ["project-task", "test", "equivalence"]
  },
  "environment": {
    "runner_class": "dedicated-pinned",
    "toolchain": "repository-pin",
    "build_mode": "release"
  },
  "protocol": {
    "warmup_seconds": 5,
    "repetitions": 15,
    "order": "random-interleaved",
    "raw_output": "artifacts/benchmark.json"
  },
  "metric": {
    "name": "latency",
    "unit": "ms",
    "statistic": "median",
    "direction": "lower",
    "max_regression_percent": 3.0,
    "minimum_effect_percent": 2.0
  },
  "verdicts": ["pass", "fail", "inconclusive"]
}
~~~

Adapters should emit raw observations and one of the three verdicts. Inconclusive is required when samples, environment equivalence, correctness, or noise do not support pass/fail.

## Gates

A positive gate requires equivalent outputs, pinned and recorded environments, warmup plus repeated raw observations, a predeclared metric/budget, variability below the decision threshold, and no unacceptable secondary regression.

Fail when the candidate breaches the budget with adequate evidence or violates correctness/resource constraints. Report inconclusive when the baseline is missing, environments differ materially, sample count is insufficient, profiler overhead dominates, variance overlaps the threshold, the workload is unrepresentative, raw results are unavailable, or only favorable runs were retained. Never convert inconclusive to pass.

## Boundaries

This skill owns benchmark design, measurement, profiling, optimization hypotheses, statistical comparison, and performance budgets. test-and-regression owns functional oracles and ordinary deterministic tests. ci-workflows owns runner scheduling and artifact plumbing. database-migrations owns migration lock/runtime budgets; database query tuning may use this skill when the requested outcome is performance rather than schema rollout.

Primary references: Google Benchmark user guidance at https://google.github.io/benchmark/user_guide.html, random interleaving at https://google.github.io/benchmark/random_interleaving.html, and Linux perf data-security guidance at https://www.kernel.org/doc/html/latest/admin-guide/perf-security.html. Use the official documentation for the selected profiler and pinned version.
