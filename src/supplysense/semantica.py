"""Búsqueda por significado sin modelos externos.

Se entrenan vectores de palabras con los títulos y descripciones de todas las compras
(unos 530 mil textos): co-ocurrencias en una ventana de 5 palabras, PPMI con suavizado y SVD.
Las palabras que aparecen en contextos parecidos ("patrulla", "sedán", "pick-up") quedan
cerca. El sitio recibe el vocabulario, los vectores cuantizados a int8 y los vectores de las
convocatorias abiertas, y calcula la similitud en el navegador. Nada sale del sitio.
"""

from __future__ import annotations

import base64
import math
import re
from collections import Counter
from collections.abc import Iterable
from typing import Any

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import svds

from .text import fold

VOCAB_SIZE = 15_000
MIN_DOCS = 5
WINDOW = 5
DIM = 64
STOPWORDS = frozenset(
    [
        "de",
        "del",
        "la",
        "las",
        "los",
        "el",
        "en",
        "y",
        "a",
        "al",
        "o",
        "u",
        "para",
        "por",
        "con",
        "sin",
        "sus",
        "su",
        "un",
        "una",
        "que",
        "se",
        "es",
        "lo",
        "le",
        "les",
        "e",
        "mas",
        "mismo",
        "misma",
        "este",
        "esta",
        "estos",
        "estas",
        "otros",
        "otras",
        "como",
        "desde",
        "hasta",
        "entre",
        "sobre",
        "segun",
        "durante",
        "ante",
        "bajo",
        "tras",
        "ser",
        "parte",
        "partes",
        "numero",
        "num",
        "no",
        "si",
        "ya",
        "the",
        "and",
        "of",
        "for",
    ]
)
_TOKEN = re.compile(r"[a-z][a-z0-9]{2,}")


def tokens(text: str | None) -> list[str]:
    """Misma tokenización que ``web/src/lib/semantica.js``."""
    return [w for w in _TOKEN.findall(fold(text)) if w not in STOPWORDS]


def train(texts: Iterable[str]) -> tuple[list[str], np.ndarray, np.ndarray]:
    """Devuelve (vocabulario, vectores normalizados, idf)."""
    docs = [tokens(t) for t in texts]
    df = Counter(w for d in docs for w in set(d))
    vocab = [w for w, c in df.most_common(VOCAB_SIZE) if c >= MIN_DOCS]
    index = {w: i for i, w in enumerate(vocab)}
    n = len(vocab)
    # Una sola secuencia con los ids de todas las palabras y WINDOW separadores (-1) entre
    # documentos: así dos palabras de documentos distintos nunca caen en la misma ventana.
    pad = [-1] * WINDOW
    seq = np.fromiter(
        (i for d in docs for i in [*(index[w] for w in d if w in index), *pad]), dtype=np.int32
    )
    rows_parts, cols_parts = [], []
    for k in range(1, WINDOW + 1):
        a, b = seq[k:], seq[:-k]
        ok = (a >= 0) & (b >= 0) & (a != b)
        rows_parts += [a[ok], b[ok]]
        cols_parts += [b[ok], a[ok]]
    rows = np.concatenate(rows_parts)
    cols = np.concatenate(cols_parts)
    counts = sparse.coo_matrix(
        (np.ones(len(rows), dtype=np.float32), (rows, cols)), shape=(n, n)
    ).tocsr()
    counts.sum_duplicates()
    total = counts.sum()
    row_sum = np.asarray(counts.sum(axis=1)).ravel()
    col_sum = np.asarray(counts.sum(axis=0)).ravel() ** 0.75  # suavizado de contexto
    col_p = col_sum / col_sum.sum()
    coo = counts.tocoo()
    pmi = np.log((coo.data / total) / ((row_sum[coo.row] / total) * col_p[coo.col]))
    keep = pmi > 0
    ppmi = sparse.csr_matrix(
        (pmi[keep].astype(np.float32), (coo.row[keep], coo.col[keep])), shape=(n, n)
    )
    total_docs = len(docs) or 1
    idf = np.array([math.log(total_docs / (1 + df[w])) for w in vocab], dtype=np.float32)
    k = min(DIM, n - 2)
    if k < 1 or ppmi.nnz == 0:
        # Corpus demasiado chico para entrenar: modelo vacío, la búsqueda por significado no
        # agrega resultados (el build no se rompe).
        return vocab, np.zeros((n, DIM), dtype=np.float32), idf
    u, s, _ = svds(ppmi, k=k, v0=np.full(n, 1 / math.sqrt(n)))  # v0 fijo: determinista
    vectors = u * np.sqrt(s)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-9
    return vocab, vectors.astype(np.float32), idf


def embed(text: str | None, index: dict[str, int], vectors: np.ndarray, idf: np.ndarray):
    ids = [index[w] for w in tokens(text) if w in index]
    if not ids:
        return None
    v = (vectors[ids] * idf[ids, None]).sum(axis=0)
    norm = np.linalg.norm(v)
    return v / norm if norm else None


def _b64(values: np.ndarray) -> str:
    q = np.clip(np.round(values * 127), -127, 127).astype(np.int8)
    return base64.b64encode(q.tobytes()).decode("ascii")


def export(texts: Iterable[str], open_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Modelo para el sitio: vocabulario, idf, vectores y los de las convocatorias abiertas."""
    vocab, vectors, idf = train(texts)
    index = {w: i for i, w in enumerate(vocab)}
    ids, docs = [], []
    for rec in open_records:
        v = embed(f"{rec.get('titulo') or ''} {rec.get('descripcion') or ''}", index, vectors, idf)
        if v is not None:
            ids.append(rec["id"])
            docs.append(v)
    return {
        "version": 1,
        "dim": int(vectors.shape[1]) if vectors.ndim == 2 else DIM,
        "stopwords": sorted(STOPWORDS),
        "vocab": vocab,
        "idf": [round(float(x), 2) for x in idf],
        "vectores": _b64(vectors),
        "ids": ids,
        "docs": _b64(np.stack(docs)) if docs else "",
    }
