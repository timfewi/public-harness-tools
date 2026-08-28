#!/bin/sh
set -eu

readonly EX_USAGE=64
readonly MAX_RUNS=1000

usage() {
  printf '%s\n' "usage: regression-gate.sh pass|fail|flake RUNS ARTIFACT_DIR [--expect TEXT] -- COMMAND [ARG ...]" >&2
  exit "$EX_USAGE"
}

die() {
  printf '%s\n' "$1" >&2
  exit "$EX_USAGE"
}

[ "$#" -ge 4 ] || usage

mode=$1
runs=$2
artifact_dir=$3
shift 3

case "$mode" in
  pass|fail|flake) ;;
  *) die "MODE must be pass, fail, or flake" ;;
esac

case "$runs" in
  ''|*[!0-9]*) die "RUNS must be a positive integer no greater than $MAX_RUNS" ;;
esac
[ "$runs" -gt 0 ] 2>/dev/null || die "RUNS must be a positive integer no greater than $MAX_RUNS"
[ "$runs" -le "$MAX_RUNS" ] 2>/dev/null || die "RUNS must be a positive integer no greater than $MAX_RUNS"

case "$artifact_dir" in
  ''|.|..|/|-*) die "ARTIFACT_DIR must name a new, dedicated directory" ;;
esac
case "/$artifact_dir/" in
  *"/../"*|*"/./"*) die "ARTIFACT_DIR must not contain dot traversal components" ;;
esac

expected_signature=
while [ "$#" -gt 0 ]; do
  case "$1" in
    --expect)
      [ "$#" -ge 2 ] || die "--expect requires a non-empty signature"
      expected_signature=$2
      [ -n "$expected_signature" ] || die "--expect requires a non-empty signature"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    *)
      die "unexpected option before --: $1"
      ;;
  esac
done
[ "$#" -gt 0 ] || die "COMMAND must not be empty"
[ "$mode" != "pass" ] || [ -z "$expected_signature" ] || die "--expect is only valid for fail or flake mode"

case "$artifact_dir" in
  */*)
    artifact_parent=${artifact_dir%/*}
    [ -n "$artifact_parent" ] || artifact_parent=/
    ;;
  *)
    artifact_parent=.
    ;;
esac

probe=$artifact_parent
while :; do
  [ ! -L "$probe" ] || die "ARTIFACT_DIR must not traverse a symbolic-link parent"
  case "$probe" in
    /|.) break ;;
    */*)
      next_probe=${probe%/*}
      [ -n "$next_probe" ] || next_probe=/
      ;;
    *)
      next_probe=.
      ;;
  esac
  [ "$next_probe" != "$probe" ] || break
  probe=$next_probe
done

[ -d "$artifact_parent" ] || die "ARTIFACT_DIR parent must already exist"
[ ! -e "$artifact_dir" ] && [ ! -L "$artifact_dir" ] || die "ARTIFACT_DIR already exists; refusing to overwrite artifacts"
mkdir "$artifact_dir" || die "could not create ARTIFACT_DIR"

set -C
argc=$#
{
  for argument do
    printf '%s\000' "$argument"
  done
} >"$artifact_dir/command.argv0"
printf 'argc=%s\n' "$argc" >"$artifact_dir/command.meta"

pass_count=0
fail_count=0
signature_mismatches=0
run_number=1
while [ "$run_number" -le "$runs" ]; do
  run_log=$artifact_dir/run-$run_number.log
  run_status=$artifact_dir/run-$run_number.status

  set +e
  "$@" >"$run_log" 2>&1
  status=$?
  set -e
  printf '%s\n' "$status" >"$run_status"

  if [ "$status" -eq 0 ]; then
    pass_count=$((pass_count + 1))
  else
    fail_count=$((fail_count + 1))
    if [ -n "$expected_signature" ]; then
      signature_found=0
      while IFS= read -r output_line || [ -n "$output_line" ]; do
        case "$output_line" in
          *"$expected_signature"*) signature_found=1; break ;;
        esac
      done <"$run_log"
      if [ "$signature_found" -eq 0 ]; then
        signature_mismatches=$((signature_mismatches + 1))
      fi
    fi
  fi
  run_number=$((run_number + 1))
done

if [ "$pass_count" -eq "$runs" ]; then
  classification=all-pass
elif [ "$fail_count" -eq "$runs" ]; then
  classification=all-fail
else
  classification=mixed
fi

gate_passed=0
case "$mode" in
  pass)
    [ "$fail_count" -eq 0 ] && gate_passed=1
    ;;
  fail)
    [ "$pass_count" -eq 0 ] && [ "$signature_mismatches" -eq 0 ] && gate_passed=1
    ;;
  flake)
    [ "$pass_count" -gt 0 ] && [ "$fail_count" -gt 0 ] && [ "$signature_mismatches" -eq 0 ] && gate_passed=1
    ;;
esac

if [ "$gate_passed" -eq 1 ]; then
  result=pass
else
  result=fail
fi

{
  printf 'mode=%s\n' "$mode"
  printf 'runs=%s\n' "$runs"
  printf 'pass=%s\n' "$pass_count"
  printf 'fail=%s\n' "$fail_count"
  printf 'classification=%s\n' "$classification"
  if [ -n "$expected_signature" ]; then
    printf 'signature_required=yes\n'
  else
    printf 'signature_required=no\n'
  fi
  printf 'signature_mismatches=%s\n' "$signature_mismatches"
  printf 'result=%s\n' "$result"
} >"$artifact_dir/summary.txt"

cat "$artifact_dir/summary.txt"
[ "$gate_passed" -eq 1 ]
