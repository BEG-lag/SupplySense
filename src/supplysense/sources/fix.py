"""Tipo de cambio FIX (pesos por dólar) que publica el repo indicadores-mx a partir del DOF."""

from __future__ import annotations

from typing import Any

from ..http import PoliteClient

URL = "https://raw.githubusercontent.com/BEG-lag/indicadores-mx/main/data/fix.json"
SINCE = "2015-01-01"


def fetch(client: PoliteClient) -> dict[str, float]:
    payload: dict[str, Any] = client.get_ok(URL).json()
    if payload.get("series") != "fix":
        raise ValueError("indicadores-mx: la serie no es FIX")
    return {
        obs["date"]: float(obs["value"])
        for obs in payload["observations"]
        if obs["date"] >= SINCE and obs.get("value")
    }
