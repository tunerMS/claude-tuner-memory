"""memtools — слой над файловой памятью Claude.

Точки (по идеям, перенятым из cognee):
  1. recall  — семантический поиск top-k чанков по корпусу memory/*.md
  2. lifecycle — протухание + near-dup → отчёт _review.md (без авто-удаления)
  3. linker  — авто-блок «Связанные» с [[links]]
  4. graphify — opt-in headless-сборка персонального графа знаний
"""

__version__ = "0.1.0"
