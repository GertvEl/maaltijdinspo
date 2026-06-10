"""
validatie.py
------------
Groentevalidatie en inputvalidatie.

Kernregel: elk recept moet minimaal GROENTE_MIN_PER_PERSOON gram groente
(vers of diepvries) per persoon bevatten. Recepten met te weinig groente
worden ofwel aangevuld, ofwel gemarkeerd als ongeldig. Uitzondering:
recepten waarbij groente het hoofdingrediënt is (bijv. salade/soep).
"""

from __future__ import annotations

import copy
from typing import Any

import config


# Gemiddeld gewicht (g) per stuk voor veelvoorkomende groenten, zodat
# "1 courgette" eerlijk meetelt in de groentevalidatie. Bewust conservatieve
# schattingen; lookup gaat op woordbasis in de productnaam.
STUKS_GRAM = {
    "ui": 100, "rode ui": 100, "sjalot": 40, "bosui": 15,
    "paprika": 150, "courgette": 300, "aubergine": 250,
    "tomaat": 75, "tomaten": 75, "cherrytomaat": 15,
    "wortel": 80, "winterwortel": 200, "winterpeen": 200,
    "prei": 150, "venkel": 250, "komkommer": 300, "pompoen": 1000,
    "broccoli": 350, "bloemkool": 700, "witlof": 120, "paksoi": 250,
    "champignon": 20, "rode biet": 120, "knolselderij": 700,
    "pastinaak": 150, "mais": 200, "maiskolf": 200, "spitskool": 700,
}


def _stuks_naar_gram(product: str) -> float:
    """Schat het gewicht in gram van één stuk van een groente (0 = onbekend).

    De langste matchende naam wint ("winterwortel" boven "wortel").
    """
    import unicodedata
    p = unicodedata.normalize("NFKD", str(product))
    p = "".join(c for c in p if not unicodedata.combining(c)).lower()
    matches = [(len(naam), gram) for naam, gram in STUKS_GRAM.items() if naam in p]
    return float(max(matches)[1]) if matches else 0.0


def _is_groente(ingredient: dict[str, Any]) -> bool:
    """Bepaal of een ingrediënt als groente telt."""
    if ingredient.get("groente") is True:
        return True
    return str(ingredient.get("categorie", "")).lower() == "groente"


def groente_gram_per_persoon(recept: dict[str, Any]) -> float:
    """Bereken het aantal gram groente per persoon in een recept.

    Telt gram-hoeveelheden direct mee; stuks worden omgerekend via de
    STUKS_GRAM-tabel (bekende groenten). Eetlepels e.d. tellen niet mee.
    """
    porties = max(0.5, float(recept.get("porties", 1)))
    totaal_g = 0.0
    for ing in recept.get("ingredienten", []):
        if not _is_groente(ing):
            continue
        eenheid = str(ing.get("eenheid", "")).lower()
        try:
            hoeveelheid = float(ing.get("hoeveelheid", 0))
        except (TypeError, ValueError):
            continue
        if eenheid in {"g", "gram"}:
            totaal_g += hoeveelheid
        elif eenheid in {"stuk", "stuks", ""} and hoeveelheid > 0:
            totaal_g += hoeveelheid * _stuks_naar_gram(ing.get("product", ""))
    return totaal_g / porties


def voldoet_aan_groente(recept: dict[str, Any]) -> bool:
    """True als het recept (al) voldoet aan de minimale groentehoeveelheid."""
    return groente_gram_per_persoon(recept) >= config.GROENTE_MIN_PER_PERSOON


def is_groente_hoofdgerecht(recept: dict[str, Any]) -> bool:
    """Uitzondering: groente is het hoofdingrediënt (salade, soep, e.d.)."""
    return bool(recept.get("groente_hoofdingredient", False))


def vul_groente_aan(recept: dict[str, Any]) -> dict[str, Any]:
    """Vul een recept aan met extra groente tot de streefwaarde is bereikt.

    Geeft een KOPIE terug; het origineel blijft ongewijzigd. Voor
    groente-hoofdgerechten wordt niets aangevuld (zie uitzondering).
    """
    recept = copy.deepcopy(recept)
    if is_groente_hoofdgerecht(recept) or voldoet_aan_groente(recept):
        return recept

    porties = max(0.5, float(recept.get("porties", 1)))
    huidige = groente_gram_per_persoon(recept)
    tekort_per_persoon = config.GROENTE_STREEF_PER_PERSOON - huidige
    if tekort_per_persoon <= 0:
        return recept

    # Verdeel het tekort over één of meer aanvulgroenten (in blokken van ~100g pp).
    toe_te_voegen_totaal = round(tekort_per_persoon * porties)
    recept.setdefault("ingredienten", [])
    recept.setdefault("aangevuld_met", [])

    index = 0
    resterend = toe_te_voegen_totaal
    while resterend > 0:
        groente = config.AANVUL_GROENTEN[index % len(config.AANVUL_GROENTEN)]
        blok = min(resterend, 100 * porties)
        recept["ingredienten"].append({
            "product": groente["product"],
            "hoeveelheid": int(blok),
            "eenheid": "g",
            "categorie": "groente",
            "groente": True,
            "biologisch": False,
        })
        recept["aangevuld_met"].append(groente["product"])
        resterend -= blok
        index += 1
        if index > 10:  # veiligheidsstop tegen oneindige lus
            break
    return recept


# --------------------------------------------------------------------------
# Inputvalidatie voor handmatig toegevoegde recepten / instellingen
# --------------------------------------------------------------------------

def valideer_nieuw_recept(recept: dict[str, Any]) -> tuple[bool, list[str]]:
    """Valideer een door de gebruiker ingevoerd recept.

    Geeft (geldig, [foutmeldingen]) terug. Voert GEEN aanvulling uit;
    dit is bedoeld om de gebruiker te informeren bij het opslaan.
    """
    fouten: list[str] = []

    naam = str(recept.get("naam", "")).strip()
    if not naam:
        fouten.append("Naam mag niet leeg zijn.")
    if len(naam) > 120:
        fouten.append("Naam is te lang (max. 120 tekens).")

    categorie = str(recept.get("categorie", "")).lower()
    if categorie not in config.TOEGESTANE_CATEGORIEEN:
        fouten.append(
            "Categorie moet één van zijn: "
            + ", ".join(config.TOEGESTANE_CATEGORIEEN) + "."
        )

    try:
        kooktijd = int(recept.get("kooktijd_min", 0))
        if kooktijd <= 0:
            fouten.append("Kooktijd moet groter zijn dan 0.")
        elif kooktijd > config.KOOKTIJD_MAX:
            fouten.append(f"Kooktijd mag max. {config.KOOKTIJD_MAX} min zijn.")
    except (TypeError, ValueError):
        fouten.append("Kooktijd moet een geheel getal zijn.")

    try:
        porties = int(recept.get("porties", 0))
        if porties <= 0:
            fouten.append("Aantal porties moet groter zijn dan 0.")
    except (TypeError, ValueError):
        fouten.append("Porties moet een geheel getal zijn.")

    ingredienten = recept.get("ingredienten", [])
    if not isinstance(ingredienten, list) or not ingredienten:
        fouten.append("Voeg minimaal één ingrediënt toe.")
    elif len(ingredienten) >= config.MAX_INGREDIENTEN:
        fouten.append(
            f"Te veel ingrediënten ({len(ingredienten)}); "
            f"houd het eenvoudig (< {config.MAX_INGREDIENTEN})."
        )

    # Groentevalidatie (tenzij groente-hoofdgerecht).
    if not is_groente_hoofdgerecht(recept) and not fouten:
        gram = groente_gram_per_persoon(recept)
        if gram < config.GROENTE_MIN_PER_PERSOON:
            fouten.append(
                f"Te weinig groente: {gram:.0f} g/persoon "
                f"(minimaal {config.GROENTE_MIN_PER_PERSOON} g vereist). "
                "Voeg verse of diepvriesgroente toe."
            )

    return (len(fouten) == 0, fouten)


def valideer_url(url: str) -> bool:
    """Eenvoudige, strikte validatie van een receptsite-URL."""
    url = str(url).strip()
    return url.startswith(("https://", "http://")) and len(url) <= 2048 and " " not in url
