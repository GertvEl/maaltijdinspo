"""
recepten.py
-----------
Beheer van recepten: laden uit de lokale database, filteren op voorkeuren,
favorieten opslaan/verwijderen en de weekselectie bijhouden.
"""

from __future__ import annotations

from typing import Any

import config
from src import opslag, validatie, gedeelde_opslag


def laad_recepten() -> list[dict[str, Any]]:
    """Laad alle lokale recepten."""
    data = opslag.laad_json(config.RECEPTEN_BESTAND, standaard=[])
    return data if isinstance(data, list) else []


def bewaar_recepten(recepten: list[dict[str, Any]]) -> None:
    opslag.schrijf_json(config.RECEPTEN_BESTAND, recepten)


def voeg_recept_toe(recept: dict[str, Any]) -> tuple[bool, list[str]]:
    """Valideer en voeg een nieuw recept toe aan de lokale database."""
    geldig, fouten = validatie.valideer_nieuw_recept(recept)
    if not geldig:
        return False, fouten
    recepten = laad_recepten()
    # Vermijd dubbele namen (case-insensitive).
    bestaande = {r.get("naam", "").lower() for r in recepten}
    if recept.get("naam", "").lower() in bestaande:
        return False, ["Er bestaat al een recept met deze naam."]
    recept.setdefault("bron", "Handmatig")
    recept.setdefault("bron_url", "")
    recepten.append(recept)
    bewaar_recepten(recepten)
    return True, []


def verwijder_recept(naam: str) -> None:
    recepten = [r for r in laad_recepten() if r.get("naam") != naam]
    bewaar_recepten(recepten)


def filter_op_voorkeuren(
    recepten: list[dict[str, Any]],
    instellingen: dict[str, Any],
) -> list[dict[str, Any]]:
    """Filter recepten op categorie, kooktijd en eenvoud.

    Recepten die te weinig groente bevatten worden NIET weggegooid maar
    later aangevuld (zie maaltijd_generator). Groente-hoofdgerechten en
    recepten die al voldoen blijven ongemoeid.
    """
    voorkeur_cats = set(instellingen.get("voorkeur_categorieen", config.TOEGESTANE_CATEGORIEEN))
    kooktijd_max = int(instellingen.get("kooktijd_max", config.KOOKTIJD_MAX))

    resultaat = []
    for r in recepten:
        if r.get("categorie", "") not in voorkeur_cats:
            continue
        try:
            kooktijd = int(r.get("kooktijd_min", 0))
        except (TypeError, ValueError):
            continue
        # Harde eis: bereidingstijd moet BEKEND zijn (>0) en max. 30 min.
        if not (0 < kooktijd <= kooktijd_max):
            continue
        if len(r.get("ingredienten", [])) >= config.MAX_INGREDIENTEN:
            continue
        resultaat.append(r)
    return resultaat


# --- Favorieten (⭐ langetermijn-inspiratie; gedeeld met het huishouden) ---

def laad_favorieten() -> list[dict[str, Any]]:
    data = gedeelde_opslag.laad(config.FAVORIETEN_BESTAND, standaard=[])
    return data if isinstance(data, list) else []


def is_favoriet(naam: str) -> bool:
    return any(f.get("naam") == naam for f in laad_favorieten())


def wissel_favoriet(recept: dict[str, Any]) -> bool:
    """Voeg toe aan of verwijder uit favorieten. Geeft de nieuwe status terug."""
    favorieten = laad_favorieten()
    naam = recept.get("naam")
    if any(f.get("naam") == naam for f in favorieten):
        favorieten = [f for f in favorieten if f.get("naam") != naam]
        gedeelde_opslag.schrijf(config.FAVORIETEN_BESTAND, favorieten)
        return False
    favorieten.append(recept)
    gedeelde_opslag.schrijf(config.FAVORIETEN_BESTAND, favorieten)
    return True


def verwijder_favoriet(naam: str) -> None:
    favorieten = [f for f in laad_favorieten() if f.get("naam") != naam]
    gedeelde_opslag.schrijf(config.FAVORIETEN_BESTAND, favorieten)


# --- Weekfavorieten (📌 de gerechten van deze week; gedeeld, basis voor
#     de boodschappenlijst) ---

def laad_weekfavorieten() -> list[dict[str, Any]]:
    data = gedeelde_opslag.laad(config.WEEKFAVORIETEN_BESTAND, standaard=[])
    return data if isinstance(data, list) else []


def is_weekfavoriet(naam: str) -> bool:
    return any(r.get("naam") == naam for r in laad_weekfavorieten())


def wissel_weekfavoriet(recept: dict[str, Any]) -> bool:
    """Zet een recept in/uit de weekfavorieten. Geeft de nieuwe status terug."""
    week = laad_weekfavorieten()
    naam = recept.get("naam")
    if any(r.get("naam") == naam for r in week):
        week = [r for r in week if r.get("naam") != naam]
        gedeelde_opslag.schrijf(config.WEEKFAVORIETEN_BESTAND, week)
        return False
    week.append(recept)
    gedeelde_opslag.schrijf(config.WEEKFAVORIETEN_BESTAND, week)
    return True


def verwijder_weekfavoriet(naam: str) -> None:
    week = [r for r in laad_weekfavorieten() if r.get("naam") != naam]
    gedeelde_opslag.schrijf(config.WEEKFAVORIETEN_BESTAND, week)


def leeg_weekfavorieten() -> None:
    gedeelde_opslag.schrijf(config.WEEKFAVORIETEN_BESTAND, [])


# --- Weekselectie ---

def bewaar_selectie(recepten: list[dict[str, Any]]) -> None:
    opslag.schrijf_json(config.GESELECTEERD_BESTAND, recepten)


def laad_selectie() -> list[dict[str, Any]]:
    data = opslag.laad_json(config.GESELECTEERD_BESTAND, standaard=[])
    return data if isinstance(data, list) else []


def bewaar_weekmenu(recepten: list[dict[str, Any]]) -> None:
    """Bewaar het volledige gegenereerde weekmenu (7 maaltijden)."""
    opslag.schrijf_json(config.WEEKMENU_BESTAND, recepten)


def laad_weekmenu() -> list[dict[str, Any]]:
    data = opslag.laad_json(config.WEEKMENU_BESTAND, standaard=[])
    return data if isinstance(data, list) else []


# --- Instellingen ---

def laad_instellingen() -> dict[str, Any]:
    data = opslag.laad_json(config.INSTELLINGEN_BESTAND, standaard={})
    instellingen = dict(config.STANDAARD_INSTELLINGEN)
    if isinstance(data, dict):
        instellingen.update(data)
    return instellingen


def bewaar_instellingen(instellingen: dict[str, Any]) -> None:
    opslag.schrijf_json(config.INSTELLINGEN_BESTAND, instellingen)
