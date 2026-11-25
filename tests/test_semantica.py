import base64

import numpy as np

from supplysense import semantica

CORPUS = (
    ["adquisicion de patrullas tipo sedan equipadas"] * 6
    + ["adquisicion de camionetas pick up para patrullaje y sedan"] * 6
    + ["compra de guantes de latex y cubrebocas desechables"] * 6
    + ["suministro de cubrebocas guantes y batas desechables"] * 6
    + ["mantenimiento de aires acondicionados en oficinas"] * 6
)


def test_tokens_fold_and_drop_stopwords():
    assert semantica.tokens("Adquisición de PATRULLAS para la SSP") == [
        "adquisicion",
        "patrullas",
        "ssp",
    ]


def test_similar_words_end_up_close(monkeypatch):
    monkeypatch.setattr(semantica, "DIM", 4)
    vocab, vectors, idf = semantica.train(CORPUS)
    index = {w: i for i, w in enumerate(vocab)}
    sim = lambda a, b: float(vectors[index[a]] @ vectors[index[b]])  # noqa: E731
    assert sim("patrullas", "sedan") > sim("patrullas", "guantes")
    assert sim("cubrebocas", "guantes") > sim("cubrebocas", "sedan")
    assert len(idf) == len(vocab)


def test_export_quantizes_and_scores_open_records(monkeypatch):
    monkeypatch.setattr(semantica, "DIM", 4)
    opens = [
        {"id": "a", "titulo": "Adquisición de patrullas"},
        {"id": "b", "titulo": "Guantes y cubrebocas"},
        {"id": "c", "titulo": "zzz"},  # sin palabras conocidas: no entra
    ]
    model = semantica.export(CORPUS, opens)
    assert model["ids"] == ["a", "b"]
    vectors = np.frombuffer(base64.b64decode(model["vectores"]), dtype=np.int8)
    docs = np.frombuffer(base64.b64decode(model["docs"]), dtype=np.int8)
    assert vectors.size == len(model["vocab"]) * 4
    assert docs.size == 2 * 4
    assert model["stopwords"] == sorted(semantica.STOPWORDS)
