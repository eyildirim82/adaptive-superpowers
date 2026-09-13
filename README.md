# Adaptive Superpowers

Adaptive Superpowers is a risk-adaptive fork of [Superpowers](https://github.com/obra/superpowers) for coding agents. It keeps Superpowers' composable engineering skills, but replaces unconditional process ceremony with a central **FAST / STANDARD / CRITICAL** execution profile and adds [Impeccable](https://github.com/pbakaus/impeccable) as the canonical frontend/UI design capability.

> **Fork status:** this repository is based on Superpowers v6.3.0. Existing Superpowers skill names remain compatible, but marketplace entries maintained by the upstream project install the upstream behavior, not this adaptive fork. Install this repository directly when you want the adaptive policy described below.

## Table of Contents

- [How it works](#how-it-works)
- [Commercial Services](#commercial-services)
- [Getting Started](#installation)
  - [ChatGPT](#chatgpt)
  - [Claude Code](#claude-code)
  - [Antigravity](#antigravity)
  - [Codex App](#codex-app)
  - [Codex CLI](#codex-cli)
  - [Cursor](#cursor)
  - [Devin CLI](#devin-cli)
  - [Factory Droid](#factory-droid)
  - [Gemini CLI](#gemini-cli)
  - [GitHub Copilot CLI](#github-copilot-cli)
  - [Grok Build CLI](#grok-build-cli)
  - [Kimi Code](#kimi-code)
  - [OpenCode](#opencode)
  - [Pi](#pi)
  - [Hermes Agent](#hermes-agent)
- [The Basic Workflow](#the-basic-workflow)
- [Community](#community)
- [What's Inside](#whats-inside)
- [Philosophy](#philosophy)
- [Contributing](#contributing)
- [Updating](#updating)
- [License](#license)
- [Visual companion telemetry](#visual-companion-telemetry)

## How it works

Every engineering task starts at the **Adaptive Orchestrator** in `using-superpowers`. It classifies risk, inherits any parent risk floor, and activates only the process strength needed for the work:

- **FAST** — narrow, local, reversible work. Minimal ceremony, targeted verification, no routine reviewer or plan artifact.
- **STANDARD** — normal feature and bug-fix work. Short design/planning when useful, TDD by default, relevant review and verification.
- **CRITICAL** — hard-risk boundaries such as production writes, destructive data changes, authorization/security changes, secrets, or irreversible external effects. Stronger isolation, review, rehearsal, and canonical verification apply.

Two invariants sit above every profile:

1. **Evidence Before Claims** — never claim a property that fresh evidence does not establish.
2. **Authorized Effects Only** — never perform an external, destructive, security-sensitive, or irreversible effect outside authority already granted by the user/task.

CRITICAL does **not** mean “ask before doing anything.” Reversible preparation, tests, rehearsal, and review continue autonomously; the agent stops only at an unauthorized effect boundary, an unresolved material product choice, or a point where every safe path would be a guess. Risk and permission are tracked separately, so an already-authorized CRITICAL action is not re-approved merely because it is critical.

For frontend/UI work, the orchestrator adds the vendored **Impeccable skill 4.3.1 (engine 0.1.5)** domain skill. Impeccable owns visual direction, layout, typography, responsive quality, accessibility-oriented visual checks, motion, and visual review; Adaptive Superpowers still owns risk, authorization, engineering verification, Git effects, and completion truthfulness.

## Commercial Services

If you're using Superpowers in enterprise and could benefit from commercial support, additional tooling, or managed spending, please don't hesitate to drop us a line at sales@primeradiant.com.

## Installation

Installation differs by harness. If you use more than one, install Adaptive Superpowers separately for each one. **Official Superpowers marketplace entries point to the upstream project.** To use this adaptive fork, install from `eyildirim82/adaptive-superpowers` wherever the harness supports GitHub/direct repository installs.

### ChatGPT

Adaptive Superpowers is a **skills-only OpenAI plugin**. For an eligible managed ChatGPT workspace, a workspace admin can import it directly from GitHub:

1. Open **Workspace settings > Plugins**.
2. Choose **Add > Import marketplace**.
3. Use `https://github.com/eyildirim82/adaptive-superpowers` as the Source.
4. Leave Path empty because `.agents/plugins/marketplace.json` is at the repository root.
5. Use `main` for continuous updates, or pin `adaptive-v0.1.0-rc2` after that tag is published.
6. Import the marketplace, then make **Adaptive Superpowers** Available or Installed for the intended roles.

Once installed, mention it with `@Adaptive Superpowers` when that control is available, or select it from the Plugins menu. Natural coding requests can also trigger its bundled skills automatically.

> GitHub marketplace import is a workspace-admin feature. Personal ChatGPT accounts may not expose custom skill/plugin import even when the Plugin Directory is visible.


#### Prompt-Handoff Parallelism in ChatGPT

When Adaptive Superpowers routes a genuine multi-branch or multi-PR convergence problem to **Controller-Gated MPD**, ordinary ChatGPT conversations use **Prompt-Handoff Parallelism** unless the runtime actually exposes isolated worker dispatch. The coordinator generates complete zero-context worker prompts for separate ChatGPT windows plus a coordinator contract; it does **not** claim that workers or agents were started.

Worker replies are navigation hints only. The coordinator independently re-checks Git/PR/Actions state before exact-head evidence or `READY@SHA` can be issued. Dependency-blocked lanes stay blocked until the canonical `.superpowers/mpd/<wave>/` ledger contains independently verified prerequisite state. Merge mutation remains separate from READY and requires `adaptive.authorization.merge == granted`.

For Claude Code, the repository also carries its existing compatible marketplace manifest:

```bash
/plugin marketplace add eyildirim82/adaptive-superpowers
/plugin install superpowers@superpowers-dev
```

### Claude Code

Superpowers is available via the [official Claude plugin marketplace](https://claude.com/plugins/superpowers)

#### Official Marketplace

- Install the plugin from Anthropic's official marketplace:

  ```bash
  /plugin install superpowers@claude-plugins-official
  ```

#### Superpowers Marketplace

The Superpowers marketplace provides Superpowers and some other related plugins for Claude Code.

- Register the marketplace:

  ```bash
  /plugin marketplace add obra/superpowers-marketplace
  ```

- Install the plugin from this marketplace:

  ```bash
  /plugin install superpowers@superpowers-marketplace
  ```

### Antigravity

Install Superpowers as a plugin from this repository:

```bash
agy plugin install https://github.com/eyildirim82/adaptive-superpowers
```

Antigravity runs the plugin's session-start hook, so Superpowers is active from
the first message. Reinstall with the same command to update.

### Codex App

If your workspace imported this repository's marketplace, open **Plugins** in Codex, search for **Adaptive Superpowers**, and install/select it. Workspace plugin policy is shared with ChatGPT where that plugin is supported.

For a local Codex checkout that is not managed through a workspace, use the manual Codex CLI installation below.

### Codex CLI

Codex plugin discovery is marketplace-based. For a user-local installation:

```bash
git clone https://github.com/eyildirim82/adaptive-superpowers.git ~/plugins/adaptive-superpowers
mkdir -p ~/.agents/plugins
```

Create or merge this entry into `~/.agents/plugins/marketplace.json`:

```json
{
  "name": "local",
  "interface": { "displayName": "Local Plugins" },
  "plugins": [
    {
      "name": "adaptive-superpowers",
      "source": {
        "source": "local",
        "path": "./plugins/adaptive-superpowers"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Developer Tools"
    }
  ]
}
```

Restart Codex, open `/plugins`, search for **Adaptive Superpowers**, and install it. If you already have a user marketplace, append the plugin entry instead of replacing the whole file.

### Cursor

- In Cursor Agent chat, install from marketplace:

  ```text
  /add-plugin superpowers
  ```

- Or search for "superpowers" in the plugin marketplace.

### Devin CLI

- Install the plugin from this repository:

  ```bash
  devin plugins install eyildirim82/adaptive-superpowers
  ```

- Update to the latest version with:

  ```bash
  devin plugins update superpowers
  ```

### Factory Droid

- Register the marketplace:

  ```bash
  droid plugin marketplace add https://github.com/eyildirim82/adaptive-superpowers
  ```

- Install the plugin:

  ```bash
  droid plugin install superpowers@superpowers
  ```

### Gemini CLI

- Install the extension:

  ```bash
  gemini extensions install https://github.com/eyildirim82/adaptive-superpowers
  ```

- Update later:

  ```bash
  gemini extensions update superpowers
  ```

### GitHub Copilot CLI

- Register the marketplace:

  ```bash
  copilot plugin marketplace add obra/superpowers-marketplace
  ```

- Install the plugin:

  ```bash
  copilot plugin install superpowers@superpowers-marketplace
  ```

### Grok Build CLI

Superpowers is available via the [official Grok plugin marketplace](https://github.com/xai-org/plugin-marketplace).

- Install the plugin from xAI's official marketplace:

  ```bash
  grok plugin install superpowers@xai-official --trust
  ```

- Or open the marketplace in the TUI, search for Superpowers, and install it:

  ```text
  /marketplace
  ```

### Kimi Code

Superpowers is available in Kimi Code's plugin marketplace.

- Open Kimi Code's plugin manager:

  ```text
  /plugins
  ```

- Go to `Marketplace` > `Superpowers` and install it.

- Or install directly from this repository:

  ```text
  /plugins install https://github.com/eyildirim82/adaptive-superpowers
  ```

- Detailed docs: [docs/README.kimi.md](docs/README.kimi.md)

### OpenCode

OpenCode uses its own plugin install; install Superpowers separately even if you
already use it in another harness.

- Tell OpenCode:

  ```
  Fetch and follow instructions from https://raw.githubusercontent.com/eyildirim82/adaptive-superpowers/refs/heads/main/.opencode/INSTALL.md
  ```

- Detailed docs: [docs/README.opencode.md](docs/README.opencode.md)

### Pi

Install Superpowers as a Pi package from this repository:

```bash
pi install git:github.com/eyildirim82/adaptive-superpowers
```

For local development, run Pi with this checkout loaded as a temporary package:

```bash
pi -e /path/to/superpowers
```

The Pi package loads the Superpowers skills and a small extension that injects the `using-superpowers` bootstrap at session startup and again after compaction. Pi has native skills, so no compatibility `Skill` tool is required. Subagent and task-list tools remain optional Pi companion packages.

### Hermes Agent

Install Superpowers as a Hermes plugin from this repository:

```bash
hermes plugins install eyildirim82/adaptive-superpowers --enable
```

Restart any active Hermes sessions after installing. Note: Hermes has no
post-compaction hook, so a very long session that compacts over its first
turn loses the bootstrap — start a fresh session if skills stop triggering.

## The Basic Workflow

The workflow is selected by the active execution profile rather than forced as one universal pipeline:

1. **using-superpowers** — routes intent through the Risk Router and establishes the execution profile.
2. **brainstorming** — explores product/design uncertainty when the profile or task actually needs it; FAST/STANDARD work has no blanket implementation-approval stop.
3. **writing-plans** — uses `none`, `lightweight`, or `persistent` planning depth. Canonical plans stay concise; worker briefs carry task-specific detail.
4. **test-driven-development** and **systematic-debugging** — apply at `opportunistic`, `default`, or `strict` / `short-root-cause`, `evidence-driven`, or `full-tracing` strength.
5. **using-git-worktrees**, **dispatching-parallel-agents**, and **subagent-driven-development** — isolate or parallelize only when the profile and coordination economics justify it. CRITICAL parallel lanes require explicit ownership contracts.
6. **requesting-code-review** — self-review, risk-based review, or independent review according to risk and diff impact; UI visual review and engineering review are composed rather than duplicated blindly.
7. **verification-before-completion** — always enforces Evidence Before Claims at targeted, relevant, or canonical scope.
8. **finishing-a-development-branch** — obeys Git authorization already present in the task. It neither asks again for granted effects nor silently invents push/merge/deploy permission.

Legacy plans that name the old skills continue to work: those names now mean “apply this capability at the active profile-selected strength,” not “override the orchestrator with unconditional ceremony.”

## Community

Upstream Superpowers is built by [Jesse Vincent](https://blog.fsck.com) and the team at [Prime Radiant](https://primeradiant.com). Adaptive Superpowers preserves that attribution and layers the adaptive policy described in this repository on top.

- **Discord**: [Join us](https://discord.gg/35wsABTejz) for community support, questions, and sharing what you're building with Superpowers
- **Upstream issues**: https://github.com/obra/superpowers/issues
- **Release announcements**: [Sign up](https://primeradiant.com/superpowers/) to get notified about new versions

## What's Inside

### Adaptive core
- **using-superpowers** — Risk Router, risk floors, execution profiles, authorization boundaries, and legacy compatibility.
- **verification-before-completion** — Evidence Before Claims.
- **finishing-a-development-branch** — intent-aware Git integration and safe cleanup.

### Engineering policies
- **brainstorming** — adaptive design exploration.
- **writing-plans** — adaptive plan resolution.
- **test-driven-development** — opportunistic/default/strict TDD.
- **systematic-debugging** — root-cause debugging scaled to risk.
- **using-git-worktrees** — current workspace / preferred isolation / required isolation.
- **dispatching-parallel-agents** — parallelism only when expected speedup beats coordination cost.
- **subagent-driven-development** and **executing-plans** — profile-aware execution and recovery.
- **requesting-code-review** / **receiving-code-review** — risk/diff-aware review.
- **writing-skills** — behavior-tested skill authoring.

### Frontend/UI domain capability
- **impeccable skill 4.3.1 (engine 0.1.5)** — vendored canonical UI/design skill with its own scripts, references, and agent metadata. Its Apache-2.0 license and third-party notice are preserved under `skills/impeccable/`. Adaptive integration rules live separately in `skills/using-superpowers/references/impeccable-adapter.md`, so the vendored source remains traceable to upstream.

## Philosophy

- **Risk-adaptive discipline** — use the smallest process that can produce trustworthy evidence.
- **Evidence before claims** — confidence never substitutes for fresh verification.
- **Authorized effects only** — autonomy stops at permissions, not at arbitrary ceremony.
- **Root cause over guessing** — debugging remains evidence-driven even when the short path is enough.
- **TDD as a tool, not a ritual** — strict where consequence demands it, lighter where test-first has low value.
- **Coordination has a cost** — plans, reviewers, worktrees, ledgers, and subagents are activated when their expected value exceeds their overhead.
- **Compatibility without policy drift** — legacy skill names remain usable but cannot silently override the active execution profile.

This fork preserves the upstream Superpowers MIT license and attribution. See the original project and release announcement for the methodology it builds upon.

## Contributing

The general contribution process for Superpowers is below. Keep in mind that we don't generally accept contributions of new skills and that any updates to skills must work across all of the coding agents we support.

1. Fork the repository
2. Switch to the 'dev' branch
3. Create a branch for your work
4. Follow the `writing-skills` skill for creating and testing new and modified skills
5. Submit a PR, being sure to fill in the pull request template.

Skill-behavior tests use the drill eval harness from [superpowers-evals](https://github.com/prime-radiant-inc/superpowers-evals/), cloned into `evals/` — see `evals/README.md` for setup. Plugin-infrastructure tests live at `tests/` and run via the relevant `run-*.sh` or `npm test`.

See `skills/writing-skills/SKILL.md` for the complete guide.

## Updating

Superpowers updates are somewhat coding-agent dependent, but are often automatic.

## License

The Superpowers-derived code is MIT licensed; see the root `LICENSE`. The vendored Impeccable skill is Apache-2.0 licensed and preserves its license and third-party notice under `skills/impeccable/`.

## Visual companion telemetry

Because skills and plugins don't provide any feedback to creators, we have no idea how many of you are using Superpowers. By default, the Prime Radiant logo on brainstorming's optional visual companion feature is loaded from our website. It includes the version of Superpowers in use. It does not include any details about your project, prompt, or coding agent. We don't see your clicks or anything about what you're building. This helps us have a rough idea of how many folks are using Superpowers and which version of Superpowers they're using. It's 100% optional. To disable this, set the environment variable `SUPERPOWERS_DISABLE_TELEMETRY` to any true value. Superpowers also honors Claude Code's `DISABLE_TELEMETRY` and `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` opt-outs.
