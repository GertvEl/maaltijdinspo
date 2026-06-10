"""
opslag.py
---------
Eenvoudige, veilige helpers voor het lokaal opslaan en laden van JSON-data.

Alle data staat LOKAAL in de map data/ (geen database, geen open poorten,
geen externe API-keys). Bestanden worden atomisch weggeschreven zodat een
crash midden in het schrijven niet leidt tot corrupte JSON.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

# Basismap van het project (één niveau boven src/)
BASIS_MAP = Path(__file__).resolve().parent.parent
DATA_MAP = BASIS_MAP / "data"
DATA_MAP.mkdir(parents=True, exist_ok=True)


def _pad(bestandsnaam: str) -> Path:
    """Bouw een veilig pad binnen de data-map.

    We staan alleen een platte bestandsnaam toe (geen / of .. ) om
    path-traversal te voorkomen.
    """
    naam = os.path.basename(bestandsnaam)
    if naam != bestandsnaam or naam in {"", ".", ".."}:
        raise ValueError(f"Ongeldige bestandsnaam: {bestandsnaam!r}")
    return DATA_MAP / naam


def laad_json(bestandsnaam: str, standaard: Any = None) -> Any:
    """Laad JSON-data; geef `standaard` terug bij een ontbrekend/corrupt bestand."""
    pad = _pad(bestandsnaam)
    if not pad.exists():
        return standaard if standaard is not None else {}
    try:
        with pad.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # Error handling: corrupte data mag de app niet laten crashen.
        return standaard if standaard is not None else {}


def schrijf_json(bestandsnaam: str, data: Any) -> None:
    """Schrijf JSON atomisch weg (eerst naar tijdelijk bestand, dan hernoemen)."""
    pad = _pad(bestandsnaam)
    tmp_fd, tmp_naam = tempfile.mkstemp(dir=str(DATA_MAP), suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_naam, pad)  # atomisch op dezelfde filesystem
    except OSError:
        # Ruim het tijdelijke bestand op als er iets misgaat.
        if os.path.exists(tmp_naam):
            os.remove(tmp_naam)
        raise
