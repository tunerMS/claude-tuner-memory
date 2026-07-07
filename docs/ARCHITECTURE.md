# Architecture & design notes

Engineering decisions behind memtools, written for contributors.

## Why a file layer instead of cognee

[cognee](https://github.com/topoteretes/cognee) is a graph+vector memory **platform**: ingest → extract triplets → store in a graph + vector DB → auto-routed retrieval. Great for large unstructured corpora, but it adds infrastructure (Postgres/pgvector or embedded stores), LLM cost per ingest, and an opaque graph.

For a personal Claude Code memory the priorities are different: the corpus is small and high-signal, and the killer feature is that notes stay **human-readable, git-friendly, and auditable**. So memtools borrows cognee's *ideas* (semantic recall, lifecycle, linking, graph) and implements them as a thin layer over the existing Markdown files — zero infra, fully local.

## memtools internals

### Chunking (`chunker.py`)
Markdown is split by headings; long sections are sub-split on paragraph boundaries up to `MAX_CHUNK_CHARS`. Frontmatter and the auto-managed `Related` block are stripped before chunking (we don't index our own output).

### Embeddings (`embed.py`) — e5 with prefixes
Default model is `intfloat/multilingual-e5-small`. e5 is an **asymmetric** retrieval model: queries are prefixed `query:` and documents `passage:`. This matters a lot for "short query → long document" recall — switching from a symmetric sentence-similarity model (paraphrase-MiniLM) to e5 turned clear misses into top hits. Prefixes auto-enable when the model name contains `e5`.

### Index (`index.py`) — incremental by content-hash
`vectors.npy` (float32, L2-normalized rows) + `meta.json` (per-file hash + row range + chunk text). On rebuild, files whose content-hash is unchanged reuse their existing rows; only changed/new files are re-embedded. The index hashes raw file content (including the auto `Related` block), so after `mem link` writes a block, that file is re-embedded **once** on the next index (vectors are identical because the block is stripped before chunking), then stabilizes — no oscillation.

### Recall (`recall.py`)
Query embedded with `query:` prefix, cosine (= dot product, vectors normalized) against the index, top-k with `file › heading` provenance. Recall uses **raw** e5 vectors — asymmetric query/passage retrieval works well as-is.

### File-vectors & anisotropy (`filevec.py`)
File-to-file operations (dedup, linking) average a file's chunk vectors. But e5 embeddings are **anisotropic** — they cluster in a narrow cone, so raw cosine is ~0.9+ for *everything*. An absolute threshold there is useless (it flagged 264 false "duplicates" on a 31-file corpus). Fix: **mean-center** the file vectors (subtract the corpus mean, renormalize) before cosine. That spreads similarities to a usable range (mean≈0, max≈0.65) and makes thresholds meaningful. Degenerate case: centering exactly 2 vectors makes them antipodal — only relevant for tiny corpora, guarded by `mat.shape[0] >= 2` and realistic in practice.

### Lifecycle (`lifecycle.py`)
Staleness by file mtime; near-dup by centered cosine. Writes `_review.md` with candidates. **Never deletes** — surfacing for human review is deliberate (don't auto-destroy curated notes).

### Linker (`linker.py`)
Top-N related files by centered cosine, written into a marker-delimited `Related (auto)` block at each note's end. Additive, idempotent (regenerated each run), removable in one pass. `MEMORY.md` (the always-loaded index) and `sessions/*` (auto-overwritten by harvester) are excluded. Link targets use each note's declared frontmatter `name:` slug so `[[ ]]` resolves.

## harvester
Parses a session transcript (`harvest.py`: user prompts in full, assistant/tool calls one-line, thinking + raw tool results dropped → a compact digest), then a small `claude --print` call summarizes it into a stable per-project slug + current-state + session-summary, upserted into `sessions/<project>.md`. `sweep.py` (launchd) only harvests idle/grown transcripts, capped per run, idempotent via `processed.json`, and skips its own summary sessions via a sentinel.

## homunculus
`capture-guard.sh` + `_capture.py` safely parse hook JSON from stdin (no code injection) and append observations, honoring the `exclude_paths` denylist. `analyze.sh` (launchd, every 30m) distills observations into instincts via `claude --print` only when enough have accumulated, then archives them. The prompt includes the ids+triggers of already-known instincts: a pattern that semantically matches one comes back as an id-only confidence bump instead of a new near-duplicate slug. `_write_instincts.py` writes/merges instinct files (confidence grows on repeat); on id-only updates it keeps the existing file's title/trigger/action/evidence instead of blanking them. `recall-instincts.sh` (SessionStart hook) injects instincts above a confidence threshold back into the session.

## Cost model
- memtools: **free** (local embeddings). The background agent runs index+lifecycle+link only.
- harvester/homunculus: a few cheap `claude` CLI calls, gated on real activity (idle/threshold checks) so tokens are spent only after work happens.
- graphify: real LLM cost, **opt-in and never on cron**.
