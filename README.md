# claude-tuner-memory

A complete, self-hosted **memory setup for [Claude Code](https://docs.claude.com/en/docs/claude-code)** — local, offline, and built on plain Markdown files you can read, diff, and version yourself.

It bundles three subsystems that turn Claude Code's flat file-memory into something that recalls semantically, learns your habits, and keeps itself tidy — without any external database, vector store, or cloud service. Inspired by [cognee](https://github.com/topoteretes/cognee)'s ideas (semantic recall, graph, lifecycle), but reimplemented as a thin layer over files instead of a separate infrastructure.

> Inline code comments and helper docs are in Russian; this README is in English. The tooling itself is language-agnostic and the embedding model is multilingual.

---

## What's inside

| Subsystem | What it does | Cost |
|---|---|---|
| **memtools** | Semantic recall + lifecycle + auto-linking + optional knowledge graph over your memory files | Local, free |
| **harvester** | Distills finished session transcripts into per-project recall files, auto-injected at the next session start in that repo | Uses `claude` CLI (cheap) |
| **homunculus** | Observes sessions via hooks, distills repeated patterns into "instincts" recalled at session start | Uses `claude` CLI (cheap) |
| **memory-convention** | The one-fact-per-file Markdown format everything builds on (drop into your `CLAUDE.md`) | — |

### memtools — the semantic layer (the core)

```
mem recall "<query>"   # top-k relevant chunks across ALL memory — use instead of reading 100KB files whole
mem index              # (re)build the semantic index (incremental, by content-hash)
mem lifecycle          # write _review.md: stale notes (>30d) + near-duplicates — NEVER deletes, only flags
mem link               # maintain a "Related (auto)" [[wikilink]] block at the bottom of each curated note
mem graphify [--deep]  # feed memory into a graphify knowledge graph (opt-in, needs an API key)
mem maintain           # index + lifecycle + link (what the launchd agent runs every 6h)
```

- **Embeddings:** `intfloat/multilingual-e5-small` (multilingual, asymmetric query/passage retrieval), local in a venv. Swap via `MEMTOOLS_MODEL`.
- **Index:** `vectors.npy` + `meta.json`, incremental — only changed files get re-embedded.
- **Anisotropy-aware:** file-to-file similarity (dedup, linking) uses **mean-centered** cosine, so the e5 "everything is 0.9+" problem doesn't produce garbage.

---

## Architecture

```
 Claude Code session
        │
        ├── hooks (PreToolUse/PostToolUse) ──▶ homunculus: observations.jsonl
        │                                          │ launchd every 30m (claude CLI)
        │                                          ▼
        │                                    instincts/personal/*.md
        │   SessionStart hook ◀── recall-instincts.sh ──┘  (injects learned prefs)
        │   SessionStart hook ◀── session-context.sh ◀── sessions/<project>.md  (last-work context)
        │   PostToolUse(Bash) ──▶ testrun-capture.sh ──▶ memory-testruns/<repo>.log (test-run history)
        │
        └── transcript .jsonl ──▶ harvester: launchd every 15m (claude CLI)
                                       │
                                       ▼
         ~/.claude/projects/<slug>/memory/        ◀── you + Claude curate notes here
            ├── MEMORY.md            (always-loaded thin index)
            ├── <note>.md            (one fact per file, frontmatter + [[links]])
            └── sessions/<project>.md (harvested recall points)
                                       │
                                       ▼
                            memtools: launchd every 6h
              index ──▶ recall (mem recall)   lifecycle ──▶ _review.md   link ──▶ [[Related]]
```

Three independent launchd agents, each with a `disabled` kill-switch. memtools is fully local; harvester/homunculus call the `claude` CLI headless for distillation.

---

## Install

Requirements: macOS (for the launchd agents), [`uv`](https://docs.astral.sh/uv/), and the `claude` CLI on `PATH` (for harvester/homunculus). Linux works for memtools/harvester/homunculus scripts but you'll need your own scheduler instead of launchd.

```bash
git clone https://github.com/tunerMS/claude-tuner-memory
cd claude-tuner-memory
./install.sh                 # full setup
# or: ./install.sh --memtools-only
# add --load-agents to also launchctl-load the background agents
```

The installer copies the subsystems into `~/.claude/`, builds the memtools venv, downloads the embedding model, and templates the launchd plists. It **does not** touch your data or auto-edit `settings.json` / `CLAUDE.md` — it prints the 3 manual steps at the end:

1. Paste `memory-convention/memory-instructions.md` into your `~/.claude/CLAUDE.md`.
2. Merge `hooks/settings.hooks.json` into `~/.claude/settings.json` (for the learning loop).
3. `launchctl load -w` the agents you want (or use `--load-agents`).

Then:

```bash
~/.claude/memory-tools/mem index
~/.claude/memory-tools/mem recall "something from your memory"
```

---

## Configuration

Everything is env-overridable (see `memtools/memtools/config.py`):

| Env | Default | Purpose |
|---|---|---|
| `MEMTOOLS_MEM_DIR` | `~/.claude/projects/<$HOME-slug>/memory` | where your memory files live |
| `MEMTOOLS_MODEL` | `intfloat/multilingual-e5-small` | embedding model |
| `MEMTOOLS_STALE_DAYS` | `30` | lifecycle staleness threshold |
| `MEMTOOLS_DUP_THRESHOLD` | `0.55` | near-dup cosine (centered) |
| `MEMTOOLS_LINK_THRESHOLD` | `0.25` | auto-link cosine (centered) |
| `CTM_MEMORY_DIR` | (same slug logic) | harvester's memory dir |

The memory dir slug is derived from `$HOME` (`/Users/alice` → `-Users-alice`), matching how Claude Code encodes the working directory. Override if you launch Claude from elsewhere.

### graphify (optional point 4)

`mem graphify` runs a headless [graphify](https://github.com/) extraction over your memory into a knowledge graph. It costs LLM tokens, so it's opt-in: put a key in `~/.claude/memory-tools/graphify.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
# or: MEMTOOLS_GRAPHIFY_BACKEND=ollama   (local, no key)
```

Without a key it skips gracefully. It's never on the background cron.

---

## Privacy

- Embeddings are computed **locally** — your notes never leave the machine.
- This repo ships **code and templates only** — no memory content, observations, or instincts.
- `homunculus/exclude_paths` lets you denylist sensitive repos so the learning loop never logs their tool I/O. Set it up first.

## Tests

```bash
cd ~/.claude/memory-tools && PYTHONPATH=. .venv/bin/pytest -q
```

## Changelog

Human-readable release notes live in [CHANGELOG.md](CHANGELOG.md).

## License

[MIT](LICENSE) © 2026 Mikhail Silin (tunerMS)
