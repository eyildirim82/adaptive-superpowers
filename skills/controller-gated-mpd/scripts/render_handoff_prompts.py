#!/usr/bin/env python3
"""Render deterministic ChatGPT Prompt-Handoff files for CG-MPD V6 waves."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

RISK_LEVELS = ("FAST", "STANDARD", "CRITICAL")
RISK_RANK = {name: index for index, name in enumerate(RISK_LEVELS)}
AUTH_ORDER = ("push", "merge", "deploy", "production_write", "destructive_action")
AUTH_VALUES = {"unknown", "granted", "denied"}
SAFE_LANE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SATISFIED_DEPENDENCY_STATUSES = {
    "satisfied",
    "merged",
    "integrated",
    "complete",
    "completed",
    "trunk-green",
    "trunk_green",
}


class RenderError(ValueError):
    """Raised when handoff input cannot be rendered safely."""


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RenderError(f"{label} unreadable: {exc}") from exc
    if not isinstance(value, dict):
        raise RenderError(f"{label} must be a JSON object")
    return value


def _nonempty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RenderError(f"{label} must be a non-empty string")
    return value.strip()


def _string_list(value: object, label: str, *, required: bool = False) -> list[str]:
    if value is None and not required:
        return []
    if not isinstance(value, list) or (required and not value):
        qualifier = "non-empty " if required else ""
        raise RenderError(f"{label} must be a {qualifier}list of strings")
    result: list[str] = []
    for item in value:
        result.append(_nonempty_string(item, label))
    return result


def _canonical_pointers(profile: dict[str, Any]) -> tuple[str, str]:
    canonical = profile.get("canonical") if isinstance(profile.get("canonical"), dict) else {}
    project = profile.get("project") if isinstance(profile.get("project"), dict) else {}
    project_profile = (
        profile.get("project_profile") if isinstance(profile.get("project_profile"), dict) else {}
    )
    spec = (
        canonical.get("spec")
        or canonical.get("spec_path")
        or canonical.get("design")
        or project.get("canonical_spec")
        or project.get("spec")
        or project_profile.get("canonical_spec")
        or project_profile.get("spec")
        or profile.get("canonical_spec")
    )
    plan = (
        canonical.get("plan")
        or canonical.get("plan_path")
        or project.get("canonical_plan")
        or project.get("plan")
        or project_profile.get("canonical_plan")
        or project_profile.get("plan")
        or profile.get("canonical_plan")
    )
    return (
        _nonempty_string(spec, "canonical spec pointer"),
        _nonempty_string(plan, "canonical plan pointer"),
    )


def _validate_profile(profile: dict[str, Any]) -> None:
    if profile.get("schema_version") != 4 or profile.get("protocol_version") != 6:
        raise RenderError("Prompt-Handoff requires CG-MPD schema 4 / protocol 6")
    _nonempty_string(profile.get("wave"), "wave")
    repository = profile.get("repository")
    if not isinstance(repository, dict):
        raise RenderError("repository must be an object")
    _nonempty_string(repository.get("repo"), "repository.repo")
    _nonempty_string(repository.get("trunk"), "repository.trunk")
    frozen = _nonempty_string(repository.get("frozen_base_sha"), "repository.frozen_base_sha")
    if len(frozen) != 40 or any(ch not in "0123456789abcdefABCDEF" for ch in frozen):
        raise RenderError("repository.frozen_base_sha must be a full 40-character hexadecimal SHA")

    adaptive = profile.get("adaptive")
    if not isinstance(adaptive, dict):
        raise RenderError("adaptive must be an object")
    if adaptive.get("transport") != "prompt-handoff":
        raise RenderError("render_handoff_prompts.py requires adaptive.transport == prompt-handoff")
    floor = adaptive.get("risk_floor")
    if floor not in RISK_RANK or RISK_RANK[str(floor)] < RISK_RANK["STANDARD"]:
        raise RenderError("adaptive.risk_floor must be STANDARD or CRITICAL")
    authorization = adaptive.get("authorization")
    if not isinstance(authorization, dict):
        raise RenderError("adaptive.authorization must be an object")
    for effect in AUTH_ORDER:
        if authorization.get(effect) not in AUTH_VALUES:
            raise RenderError(f"adaptive.authorization.{effect} must be unknown, granted, or denied")

    _canonical_pointers(profile)
    lanes = profile.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        raise RenderError("lanes must be a non-empty list")
    ids: set[str] = set()
    for lane in lanes:
        if not isinstance(lane, dict):
            raise RenderError("each lane must be an object")
        lane_id = _nonempty_string(lane.get("id"), "lane.id")
        if not SAFE_LANE_ID.fullmatch(lane_id):
            raise RenderError(f"lane id {lane_id!r} is not safe for a handoff filename")
        if lane_id in ids:
            raise RenderError(f"duplicate lane id {lane_id!r}")
        ids.add(lane_id)
        _nonempty_string(lane.get("branch"), f"lane {lane_id}.branch")
        risk = lane.get("risk", floor)
        if risk not in RISK_RANK:
            raise RenderError(f"lane {lane_id}.risk must be FAST, STANDARD, or CRITICAL")
        _string_list(lane.get("owned"), f"lane {lane_id}.owned", required=True)
        _string_list(lane.get("forbidden", []), f"lane {lane_id}.forbidden")
        _string_list(lane.get("prerequisites", []), f"lane {lane_id}.prerequisites")
        _string_list(lane.get("downstream", []), f"lane {lane_id}.downstream")
    for lane in lanes:
        lane_id = str(lane["id"])
        for dep in lane.get("prerequisites", []):
            if dep not in ids:
                raise RenderError(f"lane {lane_id}: unknown prerequisite {dep}")
            if dep == lane_id:
                raise RenderError(f"lane {lane_id}: cannot depend on itself")


def _dependency_entry(state: dict[str, Any], lane_id: str) -> object:
    lanes = state.get("lanes")
    if isinstance(lanes, dict) and lane_id in lanes:
        return lanes[lane_id]
    return state.get(lane_id)


def _dependency_status(state: dict[str, Any], lane_id: str) -> tuple[bool, str]:
    for list_key, status_name in (
        ("satisfied", "satisfied"),
        ("completed", "completed"),
        ("merged", "merged"),
        ("integrated", "integrated"),
    ):
        values = state.get(list_key)
        if isinstance(values, list) and lane_id in values:
            return True, status_name
    entry = _dependency_entry(state, lane_id)
    if entry is True:
        return True, "satisfied"
    if entry is False or entry is None:
        return False, "pending"
    if isinstance(entry, str):
        status = entry.strip().lower()
        return status in SATISFIED_DEPENDENCY_STATUSES, status or "pending"
    if isinstance(entry, dict):
        if entry.get("satisfied") is True:
            return True, str(entry.get("status") or "satisfied")
        status = str(entry.get("status") or entry.get("state") or "pending").strip().lower()
        return status in SATISFIED_DEPENDENCY_STATUSES, status
    return False, "pending"


def _prerequisite_state(
    lane: dict[str, Any], dependency_state: dict[str, Any]
) -> list[tuple[str, bool, str]]:
    return [
        (dep, *_dependency_status(dependency_state, dep))
        for dep in sorted(lane.get("prerequisites", []))
    ]


def _effective_starting_risk(profile: dict[str, Any], lane: dict[str, Any]) -> str:
    floor = str(profile["adaptive"]["risk_floor"])
    declared = str(lane.get("risk", floor))
    return max((floor, declared), key=RISK_RANK.__getitem__)


def _verification_items(profile: dict[str, Any], lane: dict[str, Any]) -> list[str]:
    for key in ("required_verification", "verification"):
        value = lane.get(key)
        if value is not None:
            if isinstance(value, str):
                return [_nonempty_string(value, f"lane {lane['id']}.{key}")]
            if isinstance(value, dict):
                commands = value.get("commands")
                if commands is not None:
                    return _string_list(commands, f"lane {lane['id']}.{key}.commands", required=True)
                gates = value.get("gates")
                if gates is not None:
                    return [f"Required gate: {item}" for item in _string_list(gates, f"lane {lane['id']}.{key}.gates", required=True)]
                raise RenderError(f"lane {lane['id']}.{key} must define commands or gates")
            return _string_list(value, f"lane {lane['id']}.{key}", required=True)

    effective = _effective_starting_risk(profile, lane)
    levels = ((profile.get("risk_policy") or {}).get("levels") or {})
    level = levels.get(effective) if isinstance(levels, dict) else None
    gate_ids = level.get("gates") if isinstance(level, dict) else None
    if not isinstance(gate_ids, list) or not gate_ids:
        return [f"Resolve and run the canonical {effective} verification gates from wave.json."]
    return [f"Required gate: {gate_id}" for gate_id in gate_ids]


def _combined_list(profile: dict[str, Any], lane: dict[str, Any], lane_keys: Iterable[str], profile_key: str) -> list[str]:
    values: list[str] = []
    profile_values = profile.get(profile_key, [])
    if isinstance(profile_values, list):
        values.extend(str(item).strip() for item in profile_values if str(item).strip())
    for key in lane_keys:
        lane_values = lane.get(key)
        if isinstance(lane_values, list):
            values.extend(str(item).strip() for item in lane_values if str(item).strip())
    return sorted(set(values))


def _reserved(lane: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("reserved", "reserved_resources", "reserved_migrations"):
        value = lane.get(key)
        if isinstance(value, str) and value.strip():
            values.append(value.strip())
        elif isinstance(value, list):
            values.extend(str(item).strip() for item in value if str(item).strip())
    return sorted(set(values))


def _task_authority(lane: dict[str, Any]) -> str:
    for key in ("task", "task_authority", "authority"):
        value = lane.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return f"Implement only lane {lane['id']} within its declared ownership contract."


def _bullet(items: Iterable[str], *, empty: str = "- none") -> str:
    values = list(items)
    if not values:
        return empty
    return "\n".join(f"- {item}" for item in values)


def _code_bullet(items: Iterable[str], *, empty: str = "- none") -> str:
    values = list(items)
    if not values:
        return empty
    return "\n".join(f"- `{item}`" for item in values)


def _worker_result_envelope() -> str:
    return """WORKER RESULT

LANE: <lane id>
RISK: <effective risk observed>
BRANCH: <assigned branch>
FROZEN_BASE: <frozen base sha>
FINAL_HEAD: <worker-reported head sha; coordinator re-verifies>
CHANGED_FILES: <paths or none>
TESTS: <commands/results>
VERIFICATION: <commands/results>
OPEN_ISSUES: <issues/blockers or none>
RISK_ESCALATIONS: <reasons or none>
READY_FOR_COORDINATOR: YES|NO"""


def _render_worker(
    profile: dict[str, Any],
    lane: dict[str, Any],
    dependency_state: dict[str, Any],
    *,
    blocked: bool,
) -> str:
    repository = profile["repository"]
    adaptive = profile["adaptive"]
    spec, plan = _canonical_pointers(profile)
    lane_id = str(lane["id"])
    prereq_state = _prerequisite_state(lane, dependency_state)
    unmet = [f"{dep} — {status}" for dep, satisfied, status in prereq_state if not satisfied]
    shared = _combined_list(
        profile,
        lane,
        ("shared", "shared_read_only", "read_only"),
        "shared_read_only",
    )
    forbidden = sorted(set(_string_list(lane.get("forbidden", []), f"lane {lane_id}.forbidden") + [
        str(item).strip() for item in profile.get("hot_zones", []) if str(item).strip()
    ]))
    title = f"# CG-MPD V6 Worker Handoff — {lane_id}"
    blocked_banner = ""
    if blocked:
        title = f"# DO NOT START — Blocked CG-MPD V6 Worker Handoff — {lane_id}"
        blocked_banner = (
            "\n> **DO NOT START.** This lane is dependency-blocked. "
            "Do not edit, commit, push, or claim execution until the coordinator regenerates a runnable prompt.\n"
            "\n## Unmet prerequisites\n"
            f"{_bullet(unmet)}\n"
        )

    auth_lines = [f"- {effect}: **{adaptive['authorization'][effect]}**" for effect in AUTH_ORDER]
    lane_auth = lane.get("authorization_boundaries")
    if isinstance(lane_auth, dict):
        auth_lines.extend(
            f"- lane boundary — {key}: **{lane_auth[key]}**" for key in sorted(lane_auth)
        )
    elif isinstance(lane_auth, list):
        auth_lines.extend(f"- lane boundary — {item}" for item in sorted(str(x).strip() for x in lane_auth if str(x).strip()))
    auth_lines.extend(
        [
            f"- branch scope: push/write authority applies only to `{lane['branch']}` when push is granted",
            f"- other branches/trunk: no write authority is implied by this handoff",
        ]
    )
    prereq_lines = [
        f"- {dep}: {'satisfied' if satisfied else 'UNMET'} ({status})"
        for dep, satisfied, status in prereq_state
    ]
    declared = str(lane.get("risk", adaptive["risk_floor"]))
    effective = _effective_starting_risk(profile, lane)

    return f"""{title}

Adaptive Superpowers + Controller-Gated MPD kullan.
{blocked_banner}
## Zero-context execution contract

- Repository: `{repository['repo']}`
- Trunk: `{repository['trunk']}`
- Wave: `{profile['wave']}`
- Canonical wave profile: `.superpowers/mpd/{profile['wave']}/wave.json`
- Canonical spec: `{spec}`
- Canonical plan: `{plan}`
- Exact task authority: {_task_authority(lane)}
- Assigned branch: `{lane['branch']}`
- Frozen base SHA: `{repository['frozen_base_sha']}`
- Inherited risk floor: **{adaptive['risk_floor']}**
- Lane declared risk: **{declared}**
- Effective starting risk floor: **{effective}**
- Transport: `prompt-handoff`

Do not expand scope beyond this lane. If required work falls outside ownership, report a blocker to the coordinator.

## Exclusive files / owned paths

{_code_bullet(sorted(lane['owned']))}

## Shared / read-only files

{_code_bullet(shared)}

## Forbidden / hot-zone paths

{_code_bullet(forbidden)}

## Reserved migrations / resources

{_code_bullet(_reserved(lane))}

## Effect authorization

{chr(10).join(auth_lines)}

Authorization is an effect boundary, not a risk level. Never infer permission from risk or from a worker result.

## Required verification

{_bullet(_verification_items(profile, lane))}

Report actual command results. A skipped command is **NOT VERIFIED**, never PASS.

## Dependency contract

Prerequisites:
{_bullet(sorted(lane.get('prerequisites', [])))}

Current prerequisite state:
{_bullet(prereq_lines)}

Downstream lanes:
{_bullet(sorted(lane.get('downstream', [])))}

- Self-READY: **FORBIDDEN**. Do not create READY or READY@SHA receipts.
- Self-merge: **FORBIDDEN**. Do not merge this branch or another lane.
- Worker output is a handoff hint only; it is **not evidence** and must not create READY.
- The coordinator must independently re-read current Git/PR/CI metadata before any authority-bearing claim.

## Worker result contract

Return exactly one compact envelope containing at least these fields:

```text
{_worker_result_envelope()}
```

`READY_FOR_COORDINATOR` only means your lane handoff appears complete. It is **not** MPD `READY@SHA`, evidence, merge approval, or merge authority.
""".rstrip() + "\n"


def _integration_order(lanes: list[dict[str, Any]]) -> list[str]:
    deps = {str(lane["id"]): set(lane.get("prerequisites", [])) for lane in lanes}
    result: list[str] = []
    remaining = set(deps)
    while remaining:
        ready = sorted(lane_id for lane_id in remaining if deps[lane_id].issubset(result))
        if not ready:
            raise RenderError("dependency cycle prevents deterministic integration order")
        result.extend(ready)
        remaining.difference_update(ready)
    return result


def _render_coordinator(
    profile: dict[str, Any], dependency_state: dict[str, Any], dispatchable: list[str], blocked: list[str]
) -> str:
    repository = profile["repository"]
    adaptive = profile["adaptive"]
    spec, plan = _canonical_pointers(profile)
    lanes = sorted(profile["lanes"], key=lambda lane: str(lane["id"]))
    lane_sections: list[str] = []
    for lane in lanes:
        lane_id = str(lane["id"])
        prereqs = sorted(lane.get("prerequisites", []))
        prereq_state = _prerequisite_state(lane, dependency_state)
        state_text = ", ".join(
            f"{dep}={'satisfied' if satisfied else status}" for dep, satisfied, status in prereq_state
        ) or "none"
        lane_sections.append(
            "\n".join(
                [
                    f"### {lane_id}",
                    f"- Branch: `{lane['branch']}`",
                    f"- Declared risk: **{lane.get('risk', adaptive['risk_floor'])}**",
                    f"- Starting effective floor: **{_effective_starting_risk(profile, lane)}**",
                    f"- Owned: {', '.join(f'`{item}`' for item in sorted(lane['owned']))}",
                    f"- Prerequisites: {', '.join(prereqs) if prereqs else 'none'}",
                    f"- Current prerequisite state: {state_text}",
                    f"- Downstream: {', '.join(sorted(lane.get('downstream', []))) if lane.get('downstream') else 'none'}",
                    f"- Reserved: {', '.join(f'`{item}`' for item in _reserved(lane)) if _reserved(lane) else 'none'}",
                ]
            )
        )
    auth_lines = [f"- {effect}: **{adaptive['authorization'][effect]}**" for effect in AUTH_ORDER]
    merge_auth = adaptive["authorization"]["merge"]
    merge_rule = (
        "Mutating merge train is authorized by the wave profile; still require valid exact-head evidence and READY before each merge."
        if merge_auth == "granted"
        else f"Mutating merge train is **NOT authorized** (`merge={merge_auth}`). Verification and READY may proceed, but stop before merge mutation."
    )

    return f"""# CG-MPD V6 Coordinator Handoff — {profile['wave']}

Adaptive Superpowers + Controller-Gated MPD kullan.

**Bu promptları ayrı ChatGPT pencerelerinde aç.** This renderer generated handoff prompts only; never claim that workers or agents were started.

## Canonical contract

- Repository: `{repository['repo']}`
- Trunk: `{repository['trunk']}`
- Wave: `{profile['wave']}`
- Frozen base SHA: `{repository['frozen_base_sha']}`
- Canonical wave profile: `.superpowers/mpd/{profile['wave']}/wave.json`
- Canonical spec: `{spec}`
- Canonical plan: `{plan}`
- Parent risk floor: **{adaptive['risk_floor']}**
- Transport: `prompt-handoff`

## Effect authorization

{chr(10).join(auth_lines)}

Risk never grants an effect. Reuse already-granted authorization and do not upgrade unknown/denied effects.

## Prompt release state

- Dispatchable lane prompts rendered now: {', '.join(f'`{item}`' for item in dispatchable) if dispatchable else 'none'}
- Dependency-blocked lanes withheld by default: {', '.join(f'`{item}`' for item in blocked) if blocked else 'none'}

## Lane contracts

{chr(10).join(lane_sections)}

## Evidence and READY rules

- Worker prose, worker-reported heads, screenshots, pasted logs, and worker result envelopes are **not evidence** and must not create READY.
- Re-read current repository, branch/PR head, base, and GitHub Actions metadata independently.
- Exact-head evidence must bind the current source head and one complete successful workflow attempt satisfying the resolved gate set.
- Only the coordinator may materialize `READY@SHA`, after all V6 evidence/profile/risk bindings are current.
- Invalidate READY when source head, base, profile, evidence, run attempt, or effective risk changes.
- V5 evidence/READY cannot authorize V6.

## Deterministic integration order

{_bullet(_integration_order(lanes))}

Serialize integration. After every permitted merge, require canonical post-merge trunk verification before advancing dependent/integration lanes.

## Merge authorization rule

{merge_rule}

## Post-merge trunk rule

After each actual merge, independently verify the new trunk SHA with the canonical trunk workflow/event/gates before treating trunk as GREEN or releasing downstream work.

## Coordinator result discipline

Do not treat `READY_FOR_COORDINATOR: YES` in a worker result as READY, evidence, approval, or merge authority. It is only a navigation hint to begin independent coordinator verification.
""".rstrip() + "\n"


def _default_output_dir(profile: dict[str, Any]) -> Path:
    return Path.cwd() / ".superpowers" / "mpd" / str(profile["wave"]) / "handoffs"


def render(
    profile: dict[str, Any],
    dependency_state: dict[str, Any],
    output_dir: Path,
    *,
    preview_blocked: bool = False,
) -> list[Path]:
    _validate_profile(profile)
    lanes = sorted(profile["lanes"], key=lambda lane: str(lane["id"]))
    dispatchable: list[str] = []
    blocked: list[str] = []
    for lane in lanes:
        lane_id = str(lane["id"])
        lane_complete, _ = _dependency_status(dependency_state, lane_id)
        if lane_complete:
            continue
        unmet = [item for item in _prerequisite_state(lane, dependency_state) if not item[1]]
        if unmet:
            blocked.append(lane_id)
        else:
            dispatchable.append(lane_id)

    by_id = {str(lane["id"]): lane for lane in lanes}
    documents: dict[str, str] = {
        "coordinator.md": _render_coordinator(profile, dependency_state, dispatchable, blocked)
    }
    for lane_id in dispatchable:
        documents[f"{lane_id}.md"] = _render_worker(
            profile, by_id[lane_id], dependency_state, blocked=False
        )
    if preview_blocked:
        for lane_id in blocked:
            documents[f"{lane_id}.md"] = _render_worker(
                profile, by_id[lane_id], dependency_state, blocked=True
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in sorted(output_dir.glob("*.md")):
        stale.unlink()

    written: list[Path] = []
    for name in sorted(documents):
        path = output_dir / name
        path.write_text(documents[name], encoding="utf-8", newline="\n")
        written.append(path)
    return written


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wave_json", type=Path, help="V6 wave.json profile")
    parser.add_argument(
        "--dependency-state",
        type=Path,
        help="JSON dependency state used to determine currently dispatchable lanes; falls back to wave.json dependency_state",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Override .superpowers/mpd/<wave>/handoffs (primarily for verification/testing)",
    )
    parser.add_argument(
        "--preview-blocked",
        action="store_true",
        help="Also render blocked lane prompts with DO NOT START and unmet prerequisites",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        profile = _load_json(args.wave_json, "wave.json")
        if args.dependency_state is not None:
            dependency_state = _load_json(args.dependency_state, "dependency state")
        else:
            embedded = profile.get("dependency_state", {})
            if not isinstance(embedded, dict):
                raise RenderError("wave.json dependency_state must be an object when present")
            dependency_state = embedded
        output_dir = args.output_dir or _default_output_dir(profile)
        written = render(profile, dependency_state, output_dir, preview_blocked=args.preview_blocked)
    except RenderError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
