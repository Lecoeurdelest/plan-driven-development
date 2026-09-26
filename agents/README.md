# Per-host manifests

Every manifest in this repository is **generated** from
[`.agent/manifest.yaml`](../.agent/manifest.yaml). Edit the manifest, never the output.

```bash
python3 scripts/render_adapters.py --check              # CI gate: fail if any manifest is stale
python3 scripts/render_adapters.py --write              # regenerate all of them
python3 scripts/render_adapters.py --package gemini-cli # build dist/ for a host with a different layout
```

| Host | Generated file | Format | Layout |
|---|---|---|---|
| OpenAI (ChatGPT, Codex, API, Atlas) | `agents/openai.yaml` | YAML, `interface` / `policy` | Installs from the repository root |
| Claude Code, Cowork | `.claude-plugin/plugin.json` | JSON; only `name` is required | Installs from the repository root |
| Gemini CLI | `gemini-extension.json` | JSON; `name` and `version` required | Needs `skills/<name>/SKILL.md` — build with `--package` |

Claude Code also reads the YAML frontmatter of `SKILL.md` directly; `plugin.json` adds
only metadata. `test_identity_is_consistent_across_hosts` fails if `skill.id`, the
frontmatter `name`, and the two JSON `name` fields ever diverge.

## Why Gemini is packaged instead of mirrored

Gemini CLI discovers a skill only at `skills/<name>/SKILL.md`. Checking in a second copy
of `SKILL.md` under `skills/` would break every relative link inside it, because
`references/` and `assets/` sit at the repository root. `--package` relocates the whole
declared `payload` into the layout Gemini expects, under `dist/`, which is not tracked.
`payload_exclude` keeps repository tooling out of the installed skill.

## Two different things are called "agent" here

| Layer | Location | Purpose | Audience |
|---|---|---|---|
| Skill packaging | `.agent/manifest.yaml` → the files above | How **this skill** is published and named on each host | Skill registries |
| Project agent contract | `.agent/` inside a **generated project** | How agents working on **the user's project** are instructed | Coding agents |

The second layer is specified in [`references/agent-contract.md`](../references/agent-contract.md).
