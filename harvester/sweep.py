#!/usr/bin/env python3
"""
Свипер жнеца: обходит транскрипты Claude Code, жнёт ЗАВЕРШЁННЫЕ (отлежавшиеся)
и новые/доросшие, идемпотентно. Запускается launchd-агентом.

Состояние: ~/.claude/harvester/processed.json  { "<path>": {size, res} }
- idle: не трогаем сессию, изменённую за последние IDLE_MIN (вероятно активна)
- growth: пережинаем, если файл вырос с прошлого раза > GROWTH (длинная сессия,
  к которой вернулись) — upsert обновит ту же запись по session-id
- sentinel: пропускаем наши собственные саммари-сессии
"""
import os, sys, json, glob, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harvester as Hv

PROJ_GLOB = os.path.expanduser("~/.claude/projects/*/*.jsonl")
STATE = os.path.expanduser("~/.claude/harvester/processed.json")
IDLE_MIN = 15
GROWTH = 2000        # байт
MAX_PER_RUN = 6      # потолок жатв за один проход — защита от всплеска расходов


def load_state():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:
        return {}


def save_state(s):
    tmp = STATE + ".tmp"
    json.dump(s, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
    os.replace(tmp, STATE)


def has_sentinel(path):
    try:
        if os.path.getsize(path) > 500_000:   # наши саммари-сессии крошечные
            return False
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return Hv.SENTINEL in fh.read()
    except Exception:
        return False


def main():
    state = load_state()
    now = time.time()
    changed = False
    done = 0
    # самые свежие (по mtime) — первыми, чтобы не отставать от реальной работы
    for path in sorted(glob.glob(PROJ_GLOB), key=lambda p: -os.path.getmtime(p)):
        if done >= MAX_PER_RUN:
            print("cap reached, остальное в следующий проход")
            break
        try:
            st = os.stat(path)
        except OSError:
            continue
        if now - st.st_mtime < IDLE_MIN * 60:          # ещё активна/свежая
            continue
        prev = state.get(path)
        if prev is not None and st.st_size - prev.get("size", 0) < GROWTH:
            continue                                    # без значимого роста
        if has_sentinel(path):
            state[path] = {"size": st.st_size, "res": "sentinel-skip"}
            changed = True
            continue
        try:
            res = Hv.harvest_transcript(path)
        except Exception as e:
            print("ERR", os.path.basename(path), repr(e)[:200])
            continue
        state[path] = {"size": st.st_size, "res": res.get("project") or res.get("skipped")}
        changed = True
        done += 1
        print("harvested", os.path.basename(path), "->", state[path]["res"])
    if changed:
        save_state(state)


if __name__ == "__main__":
    main()
