#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CASES="$ROOT/tests/adaptive-orchestrator/cases"
ASSERTIONS="$ROOT/tests/adaptive-orchestrator/assertions"
BASELINE=0
if [[ "${1:-}" == "--baseline" ]]; then BASELINE=1; shift; fi
if [[ $# -gt 0 ]]; then selected=("$@"); else mapfile -t selected < <(cd "$CASES" && printf '%s\n' *.txt | sed 's/\.txt$//'); fi
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
out="/tmp/superpowers-tests/$stamp/adaptive-orchestrator"
mkdir -p "$out"
summary="$out/summary.jsonl"
: > "$summary"
if ! command -v claude >/dev/null 2>&1; then
  for name in "${selected[@]}"; do
    jq -nc --arg case "$name" --arg mode "$([[ $BASELINE -eq 1 ]] && echo baseline || echo current)" '{case:$case,status:"not-run",reason:"claude binary unavailable",mode:$mode}' >> "$summary"
  done
  echo "Behavior evals not run: claude binary unavailable"
  echo "Report: $summary"
  exit 0
fi
failures=0
for name in "${selected[@]}"; do
  prompt="$CASES/$name.txt"; expected="$ASSERTIONS/$name.json"; log="$out/$name.jsonl"; text="$out/$name.txt"
  [[ -f "$prompt" && -f "$expected" ]] || { echo "Missing case/assertion: $name" >&2; failures=$((failures+1)); continue; }
  claude -p --plugin-dir "$ROOT" --output-format stream-json "$(cat "$prompt")" >"$log" 2>&1 || true
  jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="text") | .text' "$log" >"$text" 2>/dev/null || true
  ok=1
  while IFS= read -r s; do [[ -z "$s" || "$(cat "$text")" == *"$s"* ]] || ok=0; done < <(jq -r '.must_contain[]?' "$expected")
  while IFS= read -r s; do [[ -z "$s" || "$(tr '[:upper:]' '[:lower:]' <"$text")" != *"$(printf '%s' "$s" | tr '[:upper:]' '[:lower:]')"* ]] || ok=0; done < <(jq -r '.must_not_contain[]?' "$expected")
  status=passed; [[ $ok -eq 1 ]] || { status=failed; failures=$((failures+1)); }
  jq -nc --arg case "$name" --arg status "$status" --arg risk "$(jq -r '.expected_risk // ""' "$expected")" '{case:$case,status:$status,expected_risk:$risk}' >> "$summary"
done
cat "$summary"
echo "Report: $summary"
(( failures == 0 ))
