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
  cat <<'EOU'
usage: merge_train.sh --profile wave.json [--repo OWNER/REPO] [--approvals-dir DIR]
                      [--expected-start-sha SHA] [--timeout SECONDS]
                      [--mark-ready] [--apply] PR [PR ...]

Default mode is a non-mutating preview. --apply is honored only when the V6
profile has adaptive.authorization.merge == "granted".
EOU
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
wave = profile.get("wave")
repo = repo_cfg.get("repo")
trunk = repo_cfg.get("trunk")
frozen = repo_cfg.get("frozen_base_sha")
method = merge_cfg.get("method")
approvals = merge_cfg.get("approvals_dir")
merge_auth = authorization.get("merge")
trunk_green = merge_cfg.get("trunk_green_after_each")
if not isinstance(wave, str) or not wave or any(ch in wave for ch in ("/", "\\", "\x00")) or wave in {".", ".."}:
    raise SystemExit("profile wave is invalid for canonical MPD ledger layout")
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
values = [repo, trunk, frozen, method, approvals, merge_auth, hashlib.sha256(raw).hexdigest(), wave]
for value in values:
    sys.stdout.write(value)
    sys.stdout.write("\0")
PY
)
[[ ${#PV[@]} -eq 8 ]] || stop "could not parse V6 merge profile"
PROFILE_REPO=${PV[0]}
TRUNK=${PV[1]}
FROZEN_BASE=${PV[2]}
METHOD=${PV[3]}
PROFILE_APPROVALS=${PV[4]}
MERGE_AUTH=${PV[5]}
PROFILE_SHA=${PV[6]}
PROFILE_WAVE=${PV[7]}

if [[ -z "$REPO" ]]; then REPO=$PROFILE_REPO; fi
[[ "$REPO" == "$PROFILE_REPO" ]] || stop "--repo '$REPO' != profile repo '$PROFILE_REPO'"
if [[ -z "$APPROVALS_DIR" ]]; then APPROVALS_DIR=$PROFILE_APPROVALS; fi

mapfile -d '' -t LEDGER_PATHS < <(python3 - "$PROFILE_APPROVALS" "$APPROVALS_DIR" "$PROFILE_WAVE" <<'PY'
import sys
from pathlib import Path
profile_approvals = Path(sys.argv[1]).resolve()
requested_approvals = Path(sys.argv[2]).resolve()
wave = sys.argv[3]
if requested_approvals != profile_approvals:
    raise SystemExit(
        f"--approvals-dir {str(requested_approvals)!r} does not match profile-bound approvals_dir {str(profile_approvals)!r}"
    )
expected_suffix = (".superpowers", "mpd", wave, "approvals")
if tuple(profile_approvals.parts[-4:]) != expected_suffix:
    raise SystemExit(
        "profile merge.approvals_dir must be canonical .superpowers/mpd/<wave>/approvals"
    )
ledger_root = profile_approvals.parent
for value in (str(profile_approvals), str(ledger_root / "evidence")):
    sys.stdout.write(value)
    sys.stdout.write("\0")
PY
)
[[ ${#LEDGER_PATHS[@]} -eq 2 ]] || stop "could not resolve canonical MPD ledger paths"
APPROVALS_DIR=${LEDGER_PATHS[0]}
EVIDENCE_DIR=${LEDGER_PATHS[1]}
[[ -d "$APPROVALS_DIR" ]] || stop "canonical approvals directory not found: $APPROVALS_DIR"
[[ -d "$EVIDENCE_DIR" ]] || stop "canonical evidence directory not found: $EVIDENCE_DIR"
REPO_FLAG=(--repo "$REPO")

VERIFY_READY_SCRIPT="$SCRIPT_DIR/verify_ready.py"
CHECK_TRUNK_SCRIPT="$SCRIPT_DIR/check_trunk_evidence.py"
[[ -f "$VERIFY_READY_SCRIPT" ]] || stop "READY verifier unavailable: $VERIFY_READY_SCRIPT"
[[ -f "$CHECK_TRUNK_SCRIPT" ]] || stop "trunk evidence verifier unavailable: $CHECK_TRUNK_SCRIPT"
VERIFY_READY_CMD=(python3 "$VERIFY_READY_SCRIPT")
CHECK_TRUNK_CMD=(python3 "$CHECK_TRUNK_SCRIPT")

current_trunk_sha() {
  local output
  if ! output=$(gh api "repos/$REPO/commits/$TRUNK" --jq .sha); then
    echo "trunk metadata provider/CLI failure for $TRUNK" >&2
    return 1
  fi
  if [[ -z "$output" || "$output" == *$'\n'* || "$output" == *$'\r'* || ! "$output" =~ ^[0-9a-fA-F]{40}$ ]]; then
    echo "malformed trunk metadata for $TRUNK" >&2
    return 1
  fi
  printf '%s\n' "$output"
}

read_pr_merge_metadata() {
  local pr=$1 output rest field
  local -a fields=()
  if ! output=$(
    gh pr view "$pr" "${REPO_FLAG[@]}" \
      --json headRefOid,baseRefName,mergeable,mergeStateStatus,isDraft \
      --jq '[.headRefOid, .baseRefName, .mergeable, .mergeStateStatus, (.isDraft|tostring)] | @tsv'
  ); then
    echo "PR metadata provider/CLI failure for PR #$pr" >&2
    return 1
  fi
  if [[ -z "$output" || "$output" == *$'\n'* || "$output" == *$'\r'* ]]; then
    echo "malformed PR metadata for PR #$pr" >&2
    return 1
  fi
  rest=$output
  for _ in 1 2 3 4; do
    if [[ "$rest" != *$'\t'* ]]; then
      echo "malformed PR metadata for PR #$pr" >&2
      return 1
    fi
    field=${rest%%$'\t'*}
    fields+=("$field")
    rest=${rest#*$'\t'}
  done
  if [[ "$rest" == *$'\t'* ]]; then
    echo "malformed PR metadata for PR #$pr" >&2
    return 1
  fi
  fields+=("$rest")
  if [[ ! "${fields[0]}" =~ ^[0-9a-fA-F]{40}$ || -z "${fields[1]}" || -z "${fields[2]}" || -z "${fields[3]}" || ! "${fields[4]}" =~ ^(true|false)$ ]]; then
    echo "malformed PR metadata for PR #$pr" >&2
    return 1
  fi
  printf '%s\t%s\t%s\t%s\t%s\n' "${fields[@]}"
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
  if ! current=$(current_trunk_sha); then
    echo "STOP: trunk authority read failed during $phase" >&2
    return 2
  fi
  if [[ "$current" != "$expected" ]]; then
    echo "STOP: trunk moved unexpectedly during $phase (expected $expected, current $current)" >&2
    return 2
  fi
}

wait_pr_merged() {
  local pr=$1 start=$SECONDS state merge_oid output
  while true; do
    if ! output=$(
      gh pr view "$pr" "${REPO_FLAG[@]}" --json state,mergeCommit \
        --jq '[.state, (.mergeCommit.oid // "")] | @tsv'
    ); then
      echo "MERGED-confirmation provider/CLI failure for PR #$pr" >&2
      return 1
    fi
    if [[ -z "$output" || "$output" == *$'\n'* || "$output" != *$'\t'* ]]; then
      echo "malformed MERGED-confirmation metadata for PR #$pr" >&2
      return 1
    fi
    state=${output%%$'\t'*}
    merge_oid=${output#*$'\t'}
    if [[ -z "$state" || "$merge_oid" == *$'\t'* ]]; then
      echo "malformed MERGED-confirmation metadata for PR #$pr" >&2
      return 1
    fi
    if [[ "$state" == "MERGED" ]]; then
      if [[ ! "$merge_oid" =~ ^[0-9a-fA-F]{40}$ ]]; then
        echo "malformed MERGED-confirmation metadata for PR #$pr" >&2
        return 1
      fi
      printf '%s\n' "$merge_oid"
      return 0
    fi
    if [[ "$state" != "OPEN" || -n "$merge_oid" ]]; then
      echo "malformed MERGED-confirmation metadata for PR #$pr" >&2
      return 1
    fi
    if (( SECONDS - start >= TIMEOUT )); then
      echo "timed out waiting for PR #$pr MERGED" >&2
      return 1
    fi
    sleep "$POLL_INTERVAL"
  done
}

wait_trunk_green() {
  local sha=$1 risk=$2 start=$SECONDS output rc proof
  proof="$EVIDENCE_DIR/trunk-$sha.actions.json"
  while true; do
    if ! assert_profile_unchanged; then
      return 1
    fi
    if ! assert_trunk_sha "$sha" "post-merge evidence polling"; then
      return 1
    fi
    if output=$("${CHECK_TRUNK_CMD[@]}" \
        --profile "$PROFILE" \
        --head "$sha" \
        --effective-risk "$risk" \
        --output "$proof" 2>&1); then
      if ! python3 - "$proof" "$PROFILE_SHA" "$REPO" "$TRUNK" "$sha" "$risk" <<'PY'
import json
import sys
from pathlib import Path
proof_path = Path(sys.argv[1])
expected_profile, repo, trunk, sha, risk = sys.argv[2:]
try:
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"post-merge evidence unreadable: {exc}")
if proof.get("schema_version") != 4 or proof.get("protocol_version") != 6:
    raise SystemExit("post-merge evidence is not CG-MPD V6")
if proof.get("evidence_type") != "actions-metadata" or proof.get("metadata_authority") != "github-actions-jobs-steps":
    raise SystemExit("post-merge evidence authority is invalid")
if proof.get("source") != {"kind": "trunk", "branch": trunk}:
    raise SystemExit("post-merge evidence source is not the pinned trunk")
repository = proof.get("repository")
if not isinstance(repository, dict) or repository.get("repo") != repo or repository.get("head_sha") != sha:
    raise SystemExit("post-merge evidence repository/head binding is invalid")
if proof.get("profile_digest") != expected_profile:
    raise SystemExit("post-merge evidence profile digest differs from READY-bound profile")
risk_doc = proof.get("risk")
if not isinstance(risk_doc, dict) or risk_doc.get("effective") != risk:
    raise SystemExit("post-merge evidence risk differs from READY-bound effective risk")
required = proof.get("required_gate_ids")
if not isinstance(required, list) or not required or proof.get("satisfied_gate_ids") != required:
    raise SystemExit("post-merge evidence does not prove a complete non-empty gate set")
PY
      then
        echo "  trunk proof contract invalid after checker success" >&2
        return 1
      fi
      if ! assert_profile_unchanged; then
        return 1
      fi
      if ! assert_trunk_sha "$sha" "after post-merge evidence"; then
        return 1
      fi
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

if ! START_SHA=$(current_trunk_sha); then
  stop "could not read trunk authority at train start"
fi
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

  if ! assert_trunk_sha "$TRUNK_SHA" "preflight for PR #$PR"; then
    exit 2
  fi

  APPROVAL="$APPROVALS_DIR/pr-$PR.ready.json"
  [[ -f "$APPROVAL" ]] || stop "READY receipt missing for PR #$PR: $APPROVAL"

  # Lane B V6 authority is canonical. Resolve the exact corresponding evidence
  # from the canonical ledger by its cryptographic digest; filenames and worker
  # prose are navigation hints only and cannot select authority.
  mapfile -d '' -t RV < <(python3 - "$APPROVAL" "$EVIDENCE_DIR" <<'PY'
import hashlib
import json
import os
import re
import sys
from pathlib import Path

approval = Path(sys.argv[1])
evidence_root = Path(sys.argv[2]).resolve()
try:
    receipt = json.loads(approval.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"READY receipt unreadable: {exc}")
if not (
    receipt.get("schema_version") == 4
    and receipt.get("protocol_version") == 6
    and receipt.get("receipt_type") == "READY@SHA"
    and receipt.get("authority_role") == "controller"
):
    raise SystemExit("approval is not a controller-materialized CG-MPD V6 READY@SHA receipt")
repo_doc = receipt.get("repository")
risk_doc = receipt.get("risk")
selected = receipt.get("selected_run")
if not isinstance(repo_doc, dict) or not isinstance(risk_doc, dict) or not isinstance(selected, dict):
    raise SystemExit("READY receipt is missing canonical V6 repository/risk/selected_run objects")
repo = repo_doc.get("repo")
pr = repo_doc.get("pr")
head = repo_doc.get("head_sha")
base = repo_doc.get("base_ref")
profile_digest = receipt.get("profile_digest")
risk = risk_doc.get("effective")
run_id = selected.get("id")
attempt = selected.get("attempt")
evidence_digest = receipt.get("evidence_digest")
if not isinstance(repo, str) or not repo:
    raise SystemExit("READY receipt repository.repo is invalid")
if not isinstance(pr, int) or isinstance(pr, bool) or pr <= 0:
    raise SystemExit("READY receipt repository.pr is invalid")
if not isinstance(head, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", head):
    raise SystemExit("READY receipt repository.head_sha is invalid")
if not isinstance(base, str) or not base:
    raise SystemExit("READY receipt repository.base_ref is invalid")
if not isinstance(profile_digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", profile_digest):
    raise SystemExit("READY receipt profile_digest is invalid")
if risk not in {"FAST", "STANDARD", "CRITICAL"}:
    raise SystemExit("READY receipt effective Adaptive risk is invalid")
if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
    raise SystemExit("READY receipt selected run id is invalid")
if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt <= 0:
    raise SystemExit("READY receipt selected run attempt is invalid")
if not isinstance(evidence_digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", evidence_digest):
    raise SystemExit("READY receipt evidence_digest is invalid")
if not evidence_root.is_dir():
    raise SystemExit("canonical evidence directory is missing")

matches = []
for dirpath, dirnames, filenames in os.walk(evidence_root, followlinks=False):
    base_dir = Path(dirpath)
    dirnames[:] = sorted(name for name in dirnames if not (base_dir / name).is_symlink())
    for name in sorted(filenames):
        candidate = base_dir / name
        if candidate.is_symlink() or not candidate.is_file():
            continue
        try:
            digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
        except OSError as exc:
            raise SystemExit(f"could not hash canonical evidence candidate {candidate}: {exc}")
        if digest == evidence_digest:
            resolved = candidate.resolve()
            try:
                resolved.relative_to(evidence_root)
            except ValueError:
                raise SystemExit("evidence candidate escaped canonical ledger root")
            matches.append(resolved)
if not matches:
    raise SystemExit("no canonical evidence file matches READY evidence_digest")
if len(matches) != 1:
    raise SystemExit("ambiguous canonical evidence: multiple files match READY evidence_digest")

values = [repo, str(pr), head.lower(), base, profile_digest.lower(), risk, str(run_id), str(attempt), str(matches[0])]
for value in values:
    sys.stdout.write(value)
    sys.stdout.write("\0")
PY
  )
  [[ ${#RV[@]} -eq 9 ]] || stop "READY receipt/evidence contract invalid for PR #$PR"
  READY_REPO=${RV[0]}
  READY_PR=${RV[1]}
  READY_HEAD=${RV[2]}
  READY_BASE=${RV[3]}
  READY_PROFILE_SHA=${RV[4]}
  RISK=${RV[5]}
  READY_RUN_ID=${RV[6]}
  READY_RUN_ATTEMPT=${RV[7]}
  EVIDENCE=${RV[8]}

  [[ "$READY_REPO" == "$REPO" && "$READY_PR" == "$PR" ]] || stop "READY receipt identity mismatch for PR #$PR"
  if [[ "$READY_PROFILE_SHA" != "$PROFILE_SHA" ]]; then
    stop "merge-train profile digest does not match READY-bound profile for PR #$PR"
  fi

  if ! "${VERIFY_READY_CMD[@]}" \
      --profile "$PROFILE" \
      --receipt "$APPROVAL" \
      --evidence "$EVIDENCE"; then
    stop "READY receipt invalid or stale for PR #$PR"
  fi
  printf '  READY run=%s@%s evidence=%s\n' "$READY_RUN_ID" "$READY_RUN_ATTEMPT" "$EVIDENCE"

  if ! PR_METADATA=$(read_pr_merge_metadata "$PR"); then
    stop "live PR metadata authority read failed for PR #$PR"
  fi
  IFS=$'\t' read -r HEAD BASE_REF MERGEABLE MERGE_STATE DRAFT <<< "$PR_METADATA"
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

  if ! assert_profile_unchanged; then
    exit 2
  fi
  if ! assert_trunk_sha "$TRUNK_SHA" "immediately before merging PR #$PR"; then
    exit 2
  fi

  if [[ "$DRAFT" == "true" ]]; then
    gh pr ready "$PR" "${REPO_FLAG[@]}"
    if ! assert_profile_unchanged; then
      exit 2
    fi
    if ! assert_trunk_sha "$TRUNK_SHA" "after marking PR #$PR ready"; then
      exit 2
    fi
  fi

  if ! FINAL_PR_METADATA=$(read_pr_merge_metadata "$PR"); then
    stop "final PR metadata authority read failed for PR #$PR"
  fi
  IFS=$'\t' read -r FINAL_HEAD FINAL_BASE FINAL_MERGEABLE FINAL_MERGE_STATE FINAL_DRAFT <<< "$FINAL_PR_METADATA"
  [[ "$FINAL_HEAD" == "$HEAD" ]] || stop "PR #$PR head changed immediately before merge"
  [[ "$FINAL_BASE" == "$TRUNK" ]] || stop "PR #$PR base retargeted immediately before merge"
  [[ "$FINAL_MERGEABLE" == "MERGEABLE" && "$FINAL_MERGE_STATE" == "CLEAN" ]] || \
    stop "PR #$PR metadata stopped being GREEN immediately before merge"

  gh pr merge "$PR" "${REPO_FLAG[@]}" "--$METHOD" --match-head-commit "$HEAD"

  if ! MERGE_SHA=$(wait_pr_merged "$PR"); then
    echo "STOP: GitHub did not confirm PR #$PR MERGED" >&2
    exit 3
  fi
  if ! POST_MERGE_TRUNK=$(current_trunk_sha); then
    echo "STOP: trunk authority read failed after PR #$PR merge confirmation" >&2
    exit 3
  fi
  if [[ "$POST_MERGE_TRUNK" != "$MERGE_SHA" ]]; then
    echo "STOP: trunk moved unexpectedly after PR #$PR (merge=$MERGE_SHA trunk=$POST_MERGE_TRUNK)" >&2
    exit 3
  fi
  TRUNK_SHA=$POST_MERGE_TRUNK

  if ! wait_trunk_green "$TRUNK_SHA" "$RISK"; then
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
