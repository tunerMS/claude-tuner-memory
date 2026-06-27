"""Локальный эмбеддер. Модель грузится лениво (тяжёлый импорт torch).

Тесты НЕ зависят от модели: index/recall принимают embed_fn инъекцией.
Здесь — только продакшн-бэкенд (sentence-transformers, оффлайн после первой загрузки).
"""
import numpy as np

from . import config

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer  # ленивый импорт
        _model = SentenceTransformer(config.MODEL_NAME)
    return _model


def embed(texts: list[str], kind: str = "passage") -> np.ndarray:
    """Список строк → матрица L2-нормированных векторов (float32).

    kind: "passage" для документов (индекс), "query" для запросов — добавляет
    соответствующий e5-префикс для асимметричного retrieval.
    """
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)
    prefix = config.QUERY_PREFIX if kind == "query" else config.PASSAGE_PREFIX
    model = _get_model()
    vecs = model.encode(
        [prefix + t for t in texts],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return np.asarray(vecs, dtype=np.float32)
