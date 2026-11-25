"""Cliente HTTP cortés, compartido por todas las fuentes.

* Peticiones en serie, al menos ``min_interval`` segundos entre una y otra al mismo host.
* User-Agent genérico y descriptivo, sin datos personales.
* Reintentos con espera exponencial en errores de red, 429 y 5xx.
* Descargas grandes en streaming a disco, con GET condicional (ETag / Last-Modified).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

from . import __version__

log = logging.getLogger(__name__)

USER_AGENT = f"SupplySense/{__version__} (+https://github.com/BEG-lag/SupplySense)"
RETRY_STATUS = {429, 500, 502, 503, 504}


class FetchError(RuntimeError):
    """Una fuente no se pudo leer; quien llama lo registra y sigue."""


class PoliteClient:
    def __init__(
        self,
        *,
        min_interval: float = 1.0,
        timeout: float = 120.0,
        retries: int = 3,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.min_interval = min_interval
        self.retries = retries
        self._last: dict[str, float] = {}
        self._client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
            follow_redirects=True,
            transport=transport,
        )

    def __enter__(self) -> PoliteClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _wait(self, host: str) -> None:
        last = self._last.get(host)
        if last is not None:
            delay = self.min_interval - (time.monotonic() - last)
            if delay > 0:
                time.sleep(delay)
        self._last[host] = time.monotonic()

    def request(
        self, method: str, url: str, *, retries: int | None = None, **kwargs: Any
    ) -> httpx.Response:
        host = urlsplit(url).netloc
        error: Exception | None = None
        retries = self.retries if retries is None else retries
        for attempt in range(retries + 1):
            self._wait(host)
            try:
                response = self._client.request(method, url, **kwargs)
            except httpx.HTTPError as exc:
                error = exc
                log.warning("%s %s falló (%s), intento %d", method, url, exc, attempt + 1)
            else:
                if response.status_code not in RETRY_STATUS:
                    return response
                error = FetchError(f"HTTP {response.status_code} en {url}")
                log.warning(
                    "%s %s respondió %d, intento %d", method, url, response.status_code, attempt + 1
                )
                retry_after = response.headers.get("Retry-After", "")
                if retry_after.isdigit():
                    time.sleep(min(int(retry_after), 60))
            if attempt < retries:
                time.sleep(min(2**attempt * 2, 30))
        raise FetchError(f"Se abandona {url}: {error}")

    def get_ok(self, url: str, **kwargs: Any) -> httpx.Response:
        response = self.request("GET", url, **kwargs)
        if response.status_code != 200:
            raise FetchError(f"HTTP {response.status_code} en {url}")
        return response

    def post_ok(self, url: str, **kwargs: Any) -> httpx.Response:
        response = self.request("POST", url, **kwargs)
        if response.status_code != 200:
            raise FetchError(f"HTTP {response.status_code} en {url}")
        return response

    def download(
        self, url: str, dest: Path, validators: dict[str, str] | None = None
    ) -> dict[str, str] | None:
        """Descarga ``url`` a ``dest``. Devuelve los validadores nuevos, o None si el servidor
        dice que no cambió (304) y ``dest`` ya existe."""
        headers: dict[str, str] = {}
        if validators and dest.exists():
            if validators.get("etag"):
                headers["If-None-Match"] = validators["etag"]
            if validators.get("last_modified"):
                headers["If-Modified-Since"] = validators["last_modified"]
        host = urlsplit(url).netloc
        error: Exception | None = None
        for attempt in range(self.retries + 1):
            self._wait(host)
            tmp = dest.with_suffix(dest.suffix + ".part")
            try:
                with self._client.stream("GET", url, headers=headers) as response:
                    if response.status_code == 304:
                        return None
                    if response.status_code in RETRY_STATUS:
                        raise FetchError(f"HTTP {response.status_code} en {url}")
                    if response.status_code != 200:
                        raise FetchError(f"HTTP {response.status_code} en {url}")
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with tmp.open("wb") as fh:
                        for chunk in response.iter_bytes(1 << 20):
                            fh.write(chunk)
                    tmp.replace(dest)
                    return {
                        "etag": response.headers.get("ETag", ""),
                        "last_modified": response.headers.get("Last-Modified", ""),
                    }
            except (httpx.HTTPError, FetchError) as exc:
                error = exc
                log.warning("descarga %s falló (%s), intento %d", url, exc, attempt + 1)
                tmp.unlink(missing_ok=True)
            if attempt < self.retries:
                time.sleep(min(2**attempt * 5, 60))
        raise FetchError(f"Se abandona la descarga de {url}: {error}")
