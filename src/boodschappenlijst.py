"""
boodschappenlijst.py
--------------------
Bouwt één gecombineerde boodschappenlijst uit de geselecteerde recepten
(geschaald naar het gezin) en exporteert als CSV.

CSV-kolommen: categorie, product, hoeveelheid, eenheid, biologisch, bron_recept
"""

from __future__ import annotations

import csv
import io
from typing import Any

import pandas as pd

# Volgorde waarin categorieën in de lijst gesorteerd worden.
CATEGORIE_VOLGORDE = [
    "groente", "fruit", "vlees", "vis", "pasta", "zuivel",
    "kruiden", "saus", "overig",
]


def _categorie_sleutel(categorie: str) -> tuple[int, str]:
    cat = (categorie or "overig").lower()
    try:
        return (CATEGORIE_VOLGORDE.index(cat), cat)
    except ValueError:
        return (len(CATEGORIE_VOLGORDE), cat)


def bouw_lijst(geselecteerde_recepten: list[dict[str, Any]]) -> pd.DataFrame:
    """Combineer ingrediënten van de geselecteerde recepten tot één lijst.

    Verwacht recepten die al geschaald zijn naar het gezinsaantal porties
    (zie maaltijd_generator.schaal_recept).
    """
    samengevoegd: dict[tuple[str, str], dict[str, Any]] = {}

    for recept in geselecteerde_recepten:
        bron = recept.get("naam", "onbekend")
        for ing in recept.get("ingredienten", []):
            product = str(ing.get("product", "")).strip()
            if not product:
                continue
            eenheid = str(ing.get("eenheid", "")).strip()
            sleutel = (product.lower(), eenheid.lower())
            try:
                hoeveelheid = float(ing.get("hoeveelheid", 0))
            except (TypeError, ValueError):
                hoeveelheid = 0.0

            if sleutel not in samengevoegd:
                samengevoegd[sleutel] = {
                    "categorie": str(ing.get("categorie", "overig")).lower(),
                    "product": product,
                    "hoeveelheid": 0.0,
                    "eenheid": eenheid,
                    "biologisch": bool(ing.get("biologisch", False)),
                    "bron_recept": set(),
                }
            samengevoegd[sleutel]["hoeveelheid"] += hoeveelheid
            samengevoegd[sleutel]["bron_recept"].add(bron)

    rijen = []
    for item in samengevoegd.values():
        item["bron_recept"] = ", ".join(sorted(item["bron_recept"]))
        h = item["hoeveelheid"]
        item["hoeveelheid"] = int(h) if float(h).is_integer() else round(h, 1)
        rijen.append(item)

    rijen.sort(key=lambda r: (_categorie_sleutel(r["categorie"]), r["product"]))

    kolommen = ["categorie", "product", "hoeveelheid", "eenheid",
                "biologisch", "bron_recept"]
    return pd.DataFrame(rijen, columns=kolommen)


def naar_csv(df: pd.DataFrame) -> str:
    """Exporteer de boodschappenlijst als CSV-string (UTF-8)."""
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, quoting=csv.QUOTE_MINIMAL)
    return buffer.getvalue()
