# Changelog

What changed and why it matters, newest first. Written for humans — see `git log` for the mechanical details.

## 2026-07-07

### Added

- **Your last session's context now loads itself.** A new SessionStart hook ([hooks/session-context.sh](hooks/session-context.sh)) figures out which project you just opened Claude Code in and injects the "🔖 current state" block from that project's harvested session memory — the "so, where did we leave off?" question answers itself. Worktree checkouts resolve to the real repo name, and if the exact project has no memory file yet, you get a compact index of the projects that do instead of a wrong guess.
- **Test runs are remembered between sessions.** A new PostToolUse hook ([hooks/testrun-capture.sh](hooks/testrun-capture.sh)) spots gradle/pytest result lines in command output and keeps the last 30 per repository in `~/.claude/memory-testruns/<repo>.log`. The next session in that repo starts with your recent test results already on screen — handy for "was the suite green when I stopped yesterday?"
- **Learned instincts stop multiplying.** The homunculus analyzer now shows the model the instincts it already knows (id + trigger). When a freshly observed pattern is really an old habit under a new wording, the existing instinct's confidence grows instead of a near-duplicate slug appearing (`bash-tail-limit` next to `cap-bash-output`, etc.). Such confidence bumps update two frontmatter fields in place and never touch the instinct's text, and an unknown id arriving without content is skipped rather than written as an empty stub.

### Changed

- Homunculus analysis runs every **30 minutes instead of every 5**. Observations accumulate and are distilled in batches anyway, so this only cuts idle wake-ups and `claude` CLI spend — nothing is lost.
- Session-start instinct recall is capped at the **top 25 by confidence** (was 40) — roughly 10 KB of injected context instead of 24 KB.
- The harvester marks its own background `claude` calls with `CC_BACKGROUND=1`, and both new hooks honor that flag — automated distillation runs no longer trigger the session hooks meant for you.
- `install.sh` / `uninstall.sh` now place and remove the two new hooks; `uninstall.sh --purge-data` also clears the test-run logs.

## 2026-06-27 — Initial release

The self-hosted memory setup for Claude Code: local, offline, plain Markdown.

- **memtools** — the semantic layer over your memory files: `mem recall` (find relevant chunks without reading 100 KB files whole), `mem lifecycle` (flag stale and near-duplicate notes — never deletes), `mem link` (auto-maintained `[[wikilinks]]` between related notes), `mem graphify` (optional knowledge graph, opt-in). Local multilingual embeddings, no cloud, no database.
- **harvester** — distills finished session transcripts into per-project "current state + journal" recall files.
- **homunculus** — observes sessions via hooks and turns repeated habits into "instincts" re-injected at session start, with a denylist for sensitive repos.
- **memory-convention** — the one-fact-per-file Markdown format everything builds on, plus an installer, uninstaller, and launchd templates for the three background agents.
