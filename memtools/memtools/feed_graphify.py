"""Точка 4 — скормить память в graphify (персональный граф знаний).

Opt-in и по требованию: graphify extract вызывает LLM (платно), а в окружении
крона ключей нет. Поэтому:
  - бэкенд/ключ берём из ~/.claude/memory-tools/graphify.env (KEY=VALUE) или env;
  - ключа нет → graceful skip с понятным сообщением, без падения;
  - на агрессивный локальный крон НЕ вешаем — запускается вручную (CLI graphify).
"""
import os
import shutil
import subprocess
from pathlib import Path

from . import config

# Какой ключ → какой бэкенд graphify.
_KEY_BACKEND = [
    ("ANTHROPIC_API_KEY", "claude"),
    ("OPENAI_API_KEY", "openai"),
    ("DEEPSEEK_API_KEY", "deepseek"),
    ("GEMINI_API_KEY", "gemini"),
    ("OPENROUTER_API_KEY", "openai"),  # через OPENAI_BASE_URL=openrouter
]

GRAPH_ENV = config.TOOLS_DIR / "graphify.env"


def _load_env_file(path: Path) -> dict:
    env = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def resolve_backend() -> tuple[str | None, dict]:
    """→ (backend|None, env_overlay). None = ключей нет, надо скипнуть."""
    overlay = _load_env_file(GRAPH_ENV)
    merged = {**os.environ, **overlay}
    forced = merged.get("MEMTOOLS_GRAPHIFY_BACKEND")
    if forced:
        return forced, overlay
    for key, backend in _KEY_BACKEND:
        if merged.get(key):
            return backend, overlay
    return None, overlay


def feed(mem_dir: Path | None = None, mode_deep: bool = False) -> dict:
    """Запускает graphify extract по корпусу памяти. → статистика/skip."""
    mem_dir = mem_dir or config.MEM_DIR
    if not shutil.which("graphify"):
        return {"status": "skipped", "reason": "graphify не найден в PATH"}
    backend, overlay = resolve_backend()
    if not backend:
        return {
            "status": "skipped",
            "reason": (
                "нет API-ключа для graphify. Положи ключ в "
                f"{GRAPH_ENV} (например ANTHROPIC_API_KEY=... "
                "или MEMTOOLS_GRAPHIFY_BACKEND=ollama)"
            ),
        }

    out_dir = config.TOOLS_DIR / "graph"
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["graphify", "extract", str(mem_dir),
           "--backend", backend, "--out", str(out_dir)]
    if mode_deep:
        cmd += ["--mode", "deep"]

    run_env = {**os.environ, **overlay}
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=1800, env=run_env,
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "reason": "timeout (>30 мин)"}

    graph_json = out_dir / "graphify-out" / "graph.json"
    return {
        "status": "ok" if proc.returncode == 0 else "error",
        "backend": backend,
        "returncode": proc.returncode,
        "graph": str(graph_json) if graph_json.exists() else None,
        "tail": (proc.stdout or proc.stderr or "")[-400:],
    }
