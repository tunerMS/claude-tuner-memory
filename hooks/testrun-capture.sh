#!/bin/bash
# PostToolUse(Bash)-хук: ловит сводки прогонов тестов (gradle/pytest) в выводе
# команды и дописывает строку в ~/.claude/memory-testruns/<repo>.log.
# Лог показывается хуком session-context.sh в авто-контексте новых сессий.

[ -n "$HOMUNCULUS_ANALYZING" ] && exit 0
[ -n "$CC_BACKGROUND" ] && exit 0

# stdin читаем ДО heredoc-питона (heredoc сам занимает stdin процесса)
HOOK_INPUT=$(cat)
export HOOK_INPUT

python3 - <<'PY'
import sys, json, os, re, subprocess, datetime

try:
    d = json.loads(os.environ.get("HOOK_INPUT", ""))
except Exception:
    sys.exit(0)

if d.get("tool_name") != "Bash":
    sys.exit(0)

cmd = (d.get("tool_input") or {}).get("command", "")
out = json.dumps(d.get("tool_response") or {}, ensure_ascii=False)
# \n в JSON-строке ответа экранированы — вернём для построчных регексов
out = out.replace("\\n", "\n")

is_gradle = "gradlew" in cmd and "test" in cmd
is_pytest = "pytest" in cmd

result = None
m = re.search(r"(\d+) tests? completed, (\d+) failed(?:, (\d+) skipped)?", out)
if m:
    total, failed = int(m.group(1)), int(m.group(2))
    skipped = f", {m.group(3)} skip" if m.group(3) else ""
    result = f"{total} тестов: {total - failed} ok, {failed} FAILED{skipped}"
elif is_pytest:
    m = re.search(r"(?:(\d+) failed, )?(\d+) passed(?:, (\d+) skipped)?(?:, \d+ warning)?", out)
    f2 = re.search(r"(\d+) failed", out)
    if m or f2:
        passed = int(m.group(2)) if m else 0
        failed = int(m.group(1) or 0) if m else int(f2.group(1))
        result = f"pytest: {passed} ok, {failed} FAILED" if failed else f"pytest: {passed} ok"
elif is_gradle and "BUILD SUCCESSFUL" in out:
    result = "gradle test: зелёный (BUILD SUCCESSFUL)"
if result is None and is_gradle and "BUILD FAILED" in out and "Compilation" in out:
    result = "gradle: НЕ СКОМПИЛИРОВАЛОСЬ"

if not result:
    sys.exit(0)

cwd = d.get("cwd") or os.getcwd()
name = os.path.basename(cwd.rstrip("/"))
try:
    gc = subprocess.run(
        ["git", "-C", cwd, "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True, text=True, timeout=3,
    ).stdout.strip()
    if gc.endswith("/.git"):
        name = os.path.basename(os.path.dirname(gc))
except Exception:
    pass

cmd_short = re.sub(r"\s+", " ", cmd).strip()[:80]
line = f"{datetime.datetime.now():%Y-%m-%d %H:%M} | {result} | {cmd_short}"

log_dir = os.path.expanduser("~/.claude/memory-testruns")
os.makedirs(log_dir, exist_ok=True)
log = os.path.join(log_dir, f"{name}.log")
lines = []
if os.path.exists(log):
    lines = open(log, encoding="utf-8").read().splitlines()
lines.append(line)
open(log, "w", encoding="utf-8").write("\n".join(lines[-30:]) + "\n")
PY
exit 0
