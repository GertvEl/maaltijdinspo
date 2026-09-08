"""
voeg_recepten_toe.py
--------------------
Voegt een batchbestand met recepten veilig samen met data/recepten.json.

Gebruik (in de projectmap maaltijdinspo, met batch1.json ernaast):
    python voeg_recepten_toe.py batch1.json

Het script:
  - controleert elk nieuw recept tegen dezelfde regels als de app
    (kooktijd 1-30, < 10 ingredienten, geldige categorie, >= 150 g groente
    per persoon tenzij groente-hoofdgerecht),
  - slaat recepten met een naam of id die al bestaat over (geen dubbelingen),
  - schrijft alleen weg als het bestand daarna geldige JSON is,
  - maakt eerst een reservekopie recepten.json.bak.
"""

import json
import shutil
import sys
import unicodedata
from pathlib import Path

STUKS_GRAM = {
    "ui": 100, "rode ui": 100, "sjalot": 40, "bosui": 15, "paprika": 150,
    "courgette": 300, "aubergine": 250, "tomaat": 75, "tomaten": 75,
    "cherrytomaat": 15, "wortel": 80, "winterwortel": 200, "winterpeen": 200,
    "prei": 150, "venkel": 250, "komkommer": 300, "pompoen": 1000,
    "broccoli": 350, "bloemkool": 700, "witlof": 120, "paksoi": 250,
    "champignon": 20, "rode biet": 120, "knolselderij": 700, "pastinaak": 150,
    "mais": 200, "maiskolf": 200, "spitskool": 700,
}
GELDIGE_CAT = {"kip", "rund", "zalm", "kabeljauw", "pasta", "vegetarisch"}
GROENTE_MIN = 150
KOOKTIJD_MAX = 30
MAX_ING = 10


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def _stuks_gram(product):
    p = _norm(product)
    m = [(len(n), g) for n, g in STUKS_GRAM.items() if n in p]
    return float(max(m)[1]) if m else 0.0


def _groente_pp(r):
    porties = max(0.5, float(r.get("porties", 1)))
    tot = 0.0
    for ing in r.get("ingredienten", []):
        is_groente = ing.get("groente") is True or str(ing.get("categorie", "")).lower() == "groente"
        if not is_groente:
            continue
        e = str(ing.get("eenheid", "")).lower()
        try:
            h = float(ing.get("hoeveelheid", 0))
        except (TypeError, ValueError):
            continue
        if e in {"g", "gram"}:
            tot += h
        elif e in {"stuk", "stuks", ""} and h > 0:
            tot += h * _stuks_gram(ing.get("product", ""))
    return tot / porties


def _geldig(r):
    fouten = []
    if r.get("categorie") not in GELDIGE_CAT:
        fouten.append("ongeldige categorie")
    if not (0 < r.get("kooktijd_min", 0) <= KOOKTIJD_MAX):
        fouten.append("kooktijd niet 1-30")
    if len(r.get("ingredienten", [])) >= MAX_ING:
        fouten.append("te veel ingredienten")
    if not r.get("groente_hoofdingredient") and _groente_pp(r) < GROENTE_MIN:
        fouten.append(f"te weinig groente ({_groente_pp(r):.0f} g/pp)")
    return fouten


def main():
    if len(sys.argv) < 2:
        print("Gebruik: python voeg_recepten_toe.py <batchbestand.json>")
        sys.exit(1)

    doel = Path("data/recepten.json")
    batch = Path(sys.argv[1])
    if not doel.exists():
        print(f"FOUT: {doel} niet gevonden. Draai dit script in de projectmap.")
        sys.exit(1)
    if not batch.exists():
        print(f"FOUT: {batch} niet gevonden.")
        sys.exit(1)

    bestaand = json.loads(doel.read_text(encoding="utf-8"))
    nieuw = json.loads(batch.read_text(encoding="utf-8"))

    namen = {_norm(r.get("naam", "")) for r in bestaand}
    ids = {r.get("id") for r in bestaand}

    toegevoegd, overgeslagen, geweigerd = [], [], []
    for r in nieuw:
        fouten = _geldig(r)
        if fouten:
            geweigerd.append((r.get("naam", "?"), ", ".join(fouten)))
            continue
        if _norm(r.get("naam", "")) in namen or r.get("id") in ids:
            overgeslagen.append(r.get("naam", "?"))
            continue
        bestaand.append(r)
        namen.add(_norm(r.get("naam", "")))
        ids.add(r.get("id"))
        toegevoegd.append(r.get("naam", "?"))

    # Reservekopie en wegschrijven.
    shutil.copy(doel, doel.with_suffix(".json.bak"))
    doel.write_text(json.dumps(bestaand, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")

    print(f"Toegevoegd: {len(toegevoegd)}")
    for n in toegevoegd:
        print(f"  + {n}")
    if overgeslagen:
        print(f"Overgeslagen (bestond al): {len(overgeslagen)}")
        for n in overgeslagen:
            print(f"  = {n}")
    if geweigerd:
        print(f"Geweigerd (voldoet niet): {len(geweigerd)}")
        for n, reden in geweigerd:
            print(f"  x {n}: {reden}")
    print(f"\nTotaal recepten nu: {len(bestaand)}")
    print("Reservekopie gemaakt: data/recepten.json.bak")


if __name__ == "__main__":
    main()
