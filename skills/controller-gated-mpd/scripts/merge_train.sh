#!/usr/bin/env bash
# Serialized CG-MPD V6 merge train.
# Safe by default: plan mode never mutates GitHub. --apply may mutate only when
# adaptive.authorization.merge is explicitly "granted" in the V6 wave profile.
set -euo pipefail

PROFILE=""
REPO=""
APPROVALS_DIR=""
TIMEOUT=1800
POLL_INTERVAL=${CGMPD_POLL_INTERVAL_SECONDS:-2}
MARK_READY=0
APPLY=0
EXPECTED_START_SHA=""
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

usage() {
  cat <<'EOF'
usage: merge_train.sh --profile wave.json [--repo OWNER/REPO] [--approvals-dir DIR]
                      [--expected-start-sha SHA] [--timeout SECONDS]
                      [--mark-ready] [--apply] PR [PR ...]

Default mode is a non-mutating preview. --apply is honored only when the V6
profile has adaptive.authorization.merge == "granted".
EOF
}

stop() {
  printf 'STOP: %s\n' "$*" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      [[ $# -ge 2 ]] || stop "--profile requires a value"
      PROFILE=$2; shift 2 ;;
    --repo)
      [[ $# -ge 2 ]] || stop "--repo requires a value"
      REPO=$2; shift 2 ;;
    --approvals-dir)
      [[ $# -ge 2 ]] || stop "--approvals-dir requires a value"
      APPROVALS_DIR=$2; shift 2 ;;
    --timeout)
      [[ $# -ge 2 ]] || stop "--timeout requires a value"
      TIMEOUT=$2; shift 2 ;;
    --expected-start-sha)
      [[ $# -ge 2 ]] || stop "--expected-start-sha requires a value"
      EXPECTED_START_SHA=$2; shift 2 ;;
    --mark-ready) MARK_READY=1; shift ;;
    --apply) APPLY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    --) shift; break ;;
    -*) stop "unknown option: $1" ;;
    *) break ;;
  esac
done

[[ -n "$PROFILE" ]] || stop "--profile is required"
[[ -f "$PROFILE" ]] || stop "profile not found: $PROFILE"
[[ $# -gt 0 ]] || stop "at least one PR is required"
[[ "$TIMEOUT" =~ ^[0-9]+$ ]] || stop "--timeout must be a non-negative integer"
[[ "$POLL_INTERVAL" =~ ^[0-9]+([.][0-9]+)?$ ]] || stop "CGMPD_POLL_INTERVAL_SECONDS must be numeric"
if [[ -n "$EXPECTED_START_SHA" && ! "$EXPECTED_START_SHA" =~ ^[0-9a-fA-F]{40}$ ]]; then
  stop "--expected-start-sha must be a 40-hex SHA"
fi
command -v gh >/dev/null 2>&1 || { echo "gh CLI not found" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 not found" >&2; exit 1; }

for pr in "$@"; do
  [[ "$pr" =~ ^[1-9][0-9]*$ ]] || stop "PR identifiers must be positive numeric PR numbers: '$pr'"
done

# Parse and validate only the fields this integration boundary consumes. The
# full wave validator remains authoritative for the complete profile contract.
# NUL delimiters prevent profile-controlled newlines from corrupting field
# boundaries in the shell.
mapfile -d '' -t PV < <(python3 - "$PROFILE" <<'PY'
import hashlib
import json
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    raw = path.read_bytes()
    profile = json.loads(raw)
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"invalid wave profile: {exc}")
if profile.get("schema_version") != 4 or profile.get("protocol_version") != 6:
    raise SystemExit("profile must be CG-MPD V6 schema 4 / protocol 6")
repo_cfg = profile.get("repository") or {}
adaptive = profile.get("adaptive") or {}
authorization = adaptive.get("authorization") or {}
merge_cfg = profile.get("merge") or {}
repo = repo_cfg.get("repo")
trunk = repo_cfg.get("trunk")
frozen = repo_cfg.get("frozen_base_sha")
method = merge_cfg.get("method")
approvals = merge_cfg.get("approvals_dir")
merge_auth = authorization.get("merge")
trunk_green = merge_cfg.get("trunk_green_after_each")
if not isinstance(repo, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
    raise SystemExit("profile repository.repo is invalid")
if not isinstance(trunk, str) or not trunk or any(ch.isspace() for ch in trunk):
    raise SystemExit("profile repository.trunk is invalid")
if not isinstance(frozen, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", frozen):
    raise SystemExit("profile repository.frozen_base_sha must be a 40-hex SHA")
if method not in {"merge", "squash", "rebase"}:
    raise SystemExit("profile merge.method must be merge|squash|rebase")
if not isinstance(approvals, str) or not approvals:
    raise SystemExit("profile merge.approvals_dir is required")
if merge_auth not in {"unknown", "granted", "denied"}:
    raise SystemExit("profile adaptive.authorization.merge must be unknown|granted|denied")
if trunk_green is not True:
    raise SystemExit("profile merge.trunk_green_after_each must be true in V6")
values = [repo, trunk, frozen, method, approvals, merge_auth, hashlib.sha256(raw).hexdigest()]
for value in values:
    sys.stdout.write(value)
    sys.stdout.write("\0")
PY
)
[[ ${#PV[@]} -eq 7 ]] || stop "could not parse V6 merge profile"
PROFILE_REPO=${PV[0]}
TRUNK=${PV[1]}
FROZEN_BASE=${PV[2]}
METHOD=${PV[3]}
PROFILE_APPROVALS=${PV[4]}
MERGE_AUTH=${PV[5]}
PROFILE_SHA=${PV[6]}

if [[ -z "$REPO" ]]; then REPO=$PROFILE_REPO; fi
[[ "$REPO" == "$PROFILE_REPO" ]] || stop "--repo '$REPO' != profile repo '$PROFILE_REPO'"
if [[ -z "$APPROVALS_DIR" ]]; then APPROVALS_DIR=$PROFILE_APPROVALS; fi
REPO_FLAG=(--repo "$REPO")

VERIFY_READY_SCRIPT="$SCRIPT_DIR/verify_ready.py"
CHECK_TRUNK_SCRIPT="$SCRIPT_DIR/check_trunk_evidence.py"
[[ -f "$VERIFY_READY_SCRIPT" ]] || stop "READY verifier unavailable: $VERIFY_READY_SCRIPT"
[[ -f "$CHECK_TRUNK_SCRIPT" ]] || stop "trunk evidence verifier unavailable: $CHECK_TRUNK_SCRIPT"
VERIFY_READY_CMD=(python3 "$VERIFY_READY_SCRIPT")
CHECK_TRUNK_CMD=(python3 "$CHECK_TRUNK_SCRIPT")

current_trunk_sha() {
  gh api "repos/$REPO/commits/$TRUNK" --jq .sha
}

current_profile_sha() {
  python3 - "$PROFILE" <<'PY'
import hashlib
import sys
from pathlib import Path
print(hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest())
PY
}

assert_profile_unchanged() {
  local current
  current=$(current_profile_sha) || { echo "STOP: could not re-read wave profile before mutation" >&2; return 2; }
  if [[ "$current" != "$PROFILE_SHA" ]]; then
    echo "STOP: wave profile changed after train validation; authorization/READY binding is stale" >&2
    return 2
  fi
}

assert_trunk_sha() {
  local expected=$1 phase=$2 current
  current=$(current_trunk_sha)
  if [[ "$current" != "$expected" ]]; then
    echo "STOP: trunk moved unexpectedly during $phase (expected $expected, current $current)" >&2
    return 2
  fi
}

wait_pr_merged() {
  local pr=$1 start=$SECONDS state merge_oid
  while true; do
    IFS=$'\t' read -r state merge_oid < <(
      gh pr view "$pr" "${REPO_FLAG[@]}" --json state,mergeCommit \
        --jq '[.state, (.mergeCommit.oid // "")] | @tsv'
    )
    if [[ "$state" == "MERGED" && -n "$merge_oid" ]]; then
      printf '%s\n' "$merge_oid"
      return 0
    fi
    if (( SECONDS - start >= TIMEOUT )); then
      echo "timed out waiting for PR #$pr MERGED" >&2
      return 1
    fi
    sleep "$POLL_INTERVAL"
  done
}

wait_trunk_green() {
  local sha=$1 approval=$2 start=$SECONDS output rc
  while true; do
    if output=$("${CHECK_TRUNK_CMD[@]}" --repo "$REPO" --sha "$sha" --branch "$TRUNK" --approval "$approval" 2>&1); then
      echo "  trunk $sha is GREEN with READY-bound Adaptive risk gates"
      return 0
    else
      rc=$?
    fi
    if [[ $rc -eq 4 ]]; then
      if (( SECONDS - start >= TIMEOUT )); then
        echo "  timed out waiting for trunk metadata: $output" >&2
        return 1
      fi
      sleep "$POLL_INTERVAL"
      continue
    fi
    echo "  trunk metadata verification failed: $output" >&2
    return 1
  done
}

START_SHA=$(current_trunk_sha)
[[ -n "$EXPECTED_START_SHA" ]] || EXPECTED_START_SHA=$FROZEN_BASE
if [[ "$START_SHA" != "$EXPECTED_START_SHA" ]]; then
  stop "trunk start SHA mismatch (expected $EXPECTED_START_SHA, current $START_SHA); re-evaluate before merge or resume with an explicit Controller-pinned --expected-start-sha"
fi
printf 'Train base verified: %s @ %s\n' "$TRUNK" "$START_SHA"
printf 'Adaptive merge authorization: %s\n' "$MERGE_AUTH"

EXECUTE=0
AUTH_BLOCKED=0
if (( APPLY )); then
  if [[ "$MERGE_AUTH" == "granted" ]]; then
    EXECUTE=1
  else
    AUTH_BLOCKED=1
  fi
fi

TRUNK_SHA=$START_SHA
while [[ $# -gt 0 ]]; do
  PR=$1; shift
  printf '== PR #%s\n' "$PR"

  # Detect any movement since the train's pinned initial/previous proven SHA.
  if ! assert_trunk_sha "$TRUNK_SHA" "preflight for PR #$PR"; then
    exit 2
  fi

  APPROVAL="$APPROVALS_DIR/pr-$PR.ready.json"
  [[ -f "$APPROVAL" ]] || stop "READY receipt missing for PR #$PR: $APPROVAL"

  mapfile -d '' -t RV < <(python3 - "$APPROVAL" <<'PY'
import json
import re
import sys
from pathlib import Path
try:
    receipt = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"READY receipt unreadable: {exc}")
if not (receipt.get("schema_version") == 4 and receipt.get("protocol_version") == 6 and receipt.get("verdict") == "READY"):
    raise SystemExit("approval is not a CG-MPD V6 READY receipt")
profile = receipt.get("profile") or {}
risk = receipt.get("risk") or {}
values = [
    str(receipt.get("repo") or ""),
    str(receipt.get("pr") or ""),
    str(receipt.get("head_sha") or ""),
    str(receipt.get("base_ref") or ""),
    str(profile.get("sha256") or ""),
    str(risk.get("effective") or "unknown"),
]
if not re.fullmatch(r"[0-9a-fA-F]{40}", values[2]):
    raise SystemExit("READY receipt has invalid head SHA")
if not values[3]:
    raise SystemExit("READY receipt has empty base ref")
if not re.fullmatch(r"[0-9a-fA-F]{64}", values[4]):
    raise SystemExit("READY receipt has invalid profile digest")
if values[5] not in {"FAST", "STANDARD", "CRITICAL"}:
    raise SystemExit("READY receipt has invalid effective Adaptive risk")
for value in values:
    sys.stdout.write(value)
    sys.stdout.write("\0")
PY
  ) || stop "READY receipt invalid for PR #$PR"
  [[ ${#RV[@]} -eq 6 ]] || stop "READY receipt invalid for PR #$PR"
  READY_REPO=${RV[0]}
  READY_PR=${RV[1]}
  READY_HEAD=${RV[2]}
  READY_BASE=${RV[3]}
  READY_PROFILE_SHA=${RV[4]}
  RISK=${RV[5]}

  [[ "$READY_REPO" == "$REPO" && "$READY_PR" == "$PR" ]] || stop "READY receipt identity mismatch for PR #$PR"
  if [[ "$READY_PROFILE_SHA" != "$PROFILE_SHA" ]]; then
    stop "merge-train profile digest does not match READY-bound profile for PR #$PR"
  fi

  if ! "${VERIFY_READY_CMD[@]}" "$PR" "${REPO_FLAG[@]}" --approval "$APPROVAL"; then
    stop "READY receipt invalid or stale for PR #$PR"
  fi

  IFS=$'\t' read -r HEAD BASE_REF MERGEABLE MERGE_STATE DRAFT < <(
    gh pr view "$PR" "${REPO_FLAG[@]}" \
      --json headRefOid,baseRefName,mergeable,mergeStateStatus,isDraft \
      --jq '[.headRefOid, .baseRefName, .mergeable, .mergeStateStatus, (.isDraft|tostring)] | @tsv'
  )
  printf '  head=%s base=%s mergeable=%s state=%s draft=%s\n' "$HEAD" "$BASE_REF" "$MERGEABLE" "$MERGE_STATE" "$DRAFT"

  [[ "$READY_HEAD" == "$HEAD" ]] || stop "stale READY head for PR #$PR (READY=$READY_HEAD live=$HEAD)"
  [[ "$READY_BASE" == "$BASE_REF" ]] || stop "stale READY base for PR #$PR (READY=$READY_BASE live=$BASE_REF)"
  [[ "$BASE_REF" == "$TRUNK" ]] || stop "PR #$PR base '$BASE_REF' != train trunk '$TRUNK'"
  [[ "$MERGEABLE" == "MERGEABLE" ]] || stop "PR #$PR is $MERGEABLE; regenerate evidence/READY after update"
  [[ "$MERGE_STATE" == "CLEAN" ]] || stop "PR #$PR metadata is not GREEN/CLEAN (mergeStateStatus=$MERGE_STATE)"
  if [[ "$DRAFT" == "true" && $MARK_READY -ne 1 ]]; then
    stop "PR #$PR is Draft; pass --mark-ready explicitly"
  fi

  if (( ! EXECUTE )); then
    [[ "$DRAFT" == "true" ]] && printf '  [plan] would mark PR #%s Ready\n' "$PR"
    printf '  [plan] would merge PR #%s risk=%s with --%s --match-head-commit %s\n' "$PR" "$RISK" "$METHOD" "$HEAD"
    echo "  [plan] would prove exact resulting trunk with the same READY-bound Adaptive risk gates"
    continue
  fi

  # Close profile/trunk races between verification and the first external mutation.
  if ! assert_profile_unchanged; then
    exit 2
  fi
  if ! assert_trunk_sha "$TRUNK_SHA" "immediately before merging PR #$PR"; then
    exit 2
  fi

  if [[ "$DRAFT" == "true" ]]; then
    gh pr ready "$PR" "${REPO_FLAG[@]}"
    # Marking Ready is itself an external mutation; re-pin trunk before merge.
    if ! assert_profile_unchanged; then
      exit 2
    fi
    if ! assert_trunk_sha "$TRUNK_SHA" "after marking PR #$PR ready"; then
      exit 2
    fi
  fi

  # Re-resolve live PR identity immediately before merge. Exact-head protection is
  # atomic for the head; this additional check minimizes base-retarget TOCTOU.
  IFS=$'\t' read -r FINAL_HEAD FINAL_BASE FINAL_MERGEABLE FINAL_MERGE_STATE FINAL_DRAFT < <(
    gh pr view "$PR" "${REPO_FLAG[@]}" \
      --json headRefOid,baseRefName,mergeable,mergeStateStatus,isDraft \
      --jq '[.headRefOid, .baseRefName, .mergeable, .mergeStateStatus, (.isDraft|tostring)] | @tsv'
  )
  [[ "$FINAL_HEAD" == "$HEAD" ]] || stop "PR #$PR head changed immediately before merge"
  [[ "$FINAL_BASE" == "$TRUNK" ]] || stop "PR #$PR base retargeted immediately before merge"
  [[ "$FINAL_MERGEABLE" == "MERGEABLE" && "$FINAL_MERGE_STATE" == "CLEAN" ]] || \
    stop "PR #$PR metadata stopped being GREEN immediately before merge"

  gh pr merge "$PR" "${REPO_FLAG[@]}" "--$METHOD" --match-head-commit "$HEAD"

  if ! MERGE_SHA=$(wait_pr_merged "$PR"); then
    echo "STOP: GitHub did not confirm PR #$PR MERGED" >&2
    exit 3
  fi
  POST_MERGE_TRUNK=$(current_trunk_sha)
  if [[ "$POST_MERGE_TRUNK" != "$MERGE_SHA" ]]; then
    echo "STOP: trunk moved unexpectedly after PR #$PR (merge=$MERGE_SHA trunk=$POST_MERGE_TRUNK)" >&2
    exit 3
  fi
  TRUNK_SHA=$POST_MERGE_TRUNK

  if ! wait_trunk_green "$TRUNK_SHA" "$APPROVAL"; then
    echo "STOP: trunk not GREEN after PR #$PR at $TRUNK_SHA" >&2
    exit 3
  fi
done

if (( AUTH_BLOCKED )); then
  echo "STOP: --apply requires adaptive.authorization.merge == granted (current: $MERGE_AUTH); preview completed without mutation" >&2
  exit 2
fi
if (( EXECUTE )); then
  echo "Merge train complete; trunk $TRUNK_SHA is GREEN."
else
  echo "Plan complete; nothing was merged. Re-run with --apply only when Adaptive merge authorization is granted."
fi
