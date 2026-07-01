"""
maaltijd_generator.py
----------------------
Genereert een weekmenu van 10 maaltijden met variatie en minimaal 1
vegetarisch recept. Elk geselecteerd recept wordt door de groentevalidatie
gehaald en indien nodig aangevuld.
"""

from __future__ import annotations

import copy
import random
from typing import Any

import config
from src import validatie


def _markeer_groente(recept: dict[str, Any]) -> dict[str, Any]:
    """Bereken en zet de groentehoeveelheid per persoon op het recept.

    Voegt ook een vlag toe of het recept oorspronkelijk voldeed of is
    aangevuld (handig voor de push-notificatie/waarschuwing in de UI).
    """
    voldeed_origineel = validatie.voldoet_aan_groente(recept) or validatie.is_groente_hoofdgerecht(recept)
    aangevuld = validatie.vul_groente_aan(recept)
    aangevuld["groente_per_persoon"] = round(validatie.groente_gram_per_persoon(aangevuld))
    aangevuld["voldeed_origineel"] = voldeed_origineel
    aangevuld["is_aangevuld"] = bool(aangevuld.get("aangevuld_met"))
    return aangevuld


def _is_aardappelgerecht(recept: dict[str, Any]) -> bool:
    """True als het recept een aardappel- of aardappelachtige bijgerecht bevat."""
    for ing in recept.get("ingredienten", []):
        product = str(ing.get("product", "")).lower()
        if any(token in product for token in ["aardappel", "krieltjes", "friet", "patat"]):
            return True
    return False


def schaal_recept(recept: dict[str, Any], doel_porties: float) -> dict[str, Any]:
    """Schaal alle ingrediënthoeveelheden naar het gewenste aantal porties.

    Geeft een kopie terug. Gram/ml worden afgerond op hele getallen,
    kleine eenheden (el/tl/stuk) op halven.
    """
    recept = copy.deepcopy(recept)
    huidig = max(0.5, float(recept.get("porties", 1)))
    factor = doel_porties / huidig
    if abs(factor - 1.0) < 0.01:
        recept["porties"] = doel_porties
        return recept

    for ing in recept.get("ingredienten", []):
        try:
            h = float(ing.get("hoeveelheid", 0))
        except (TypeError, ValueError):
            continue
        if h <= 0:
            continue
        nieuw = h * factor
        if str(ing.get("eenheid", "")).lower() in {"g", "gram", "ml"}:
            nieuw = round(nieuw)
        else:
            nieuw = round(nieuw * 2) / 2  # halve stuks/lepels toegestaan
        ing["hoeveelheid"] = int(nieuw) if float(nieuw).is_integer() else nieuw
    recept["porties"] = doel_porties
    return recept


def genereer_weekmenu(
    beschikbare_recepten: list[dict[str, Any]],
    instellingen: dict[str, Any] | None = None,
    seed: int | None = None,
    favoriete_namen: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Genereer een weekmenu.

    Favorieten (favoriete_namen) worden alleen meegewogen als
    ``instellingen["favorieten_voorrang"]`` True is; standaard worden
    recepten willekeurig geselecteerd.

    Retourneert (maaltijden, waarschuwingen).
    """
    instellingen = instellingen or dict(config.STANDAARD_INSTELLINGEN)
    favoriete_namen = favoriete_namen or set()
    waarschuwingen: list[str] = []
    rng = random.Random(seed)

    if not beschikbare_recepten:
        return [], ["Geen recepten beschikbaar om een menu te genereren."]

    pool = list(beschikbare_recepten)
    rng.shuffle(pool)

    vegetarisch = [r for r in pool if r.get("vegetarisch")]
    niet_veg = [r for r in pool if not r.get("vegetarisch")]

    gekozen: list[dict[str, Any]] = []
    gebruikte_categorieen: list[str] = []

    def is_fav(recept: dict[str, Any]) -> bool:
        return recept.get("naam", "") in favoriete_namen

    def is_toegestaan(recept: dict[str, Any]) -> bool:
        categorie = str(recept.get("categorie", "")).lower()
        if _is_aardappelgerecht(recept):
            if sum(1 for g in gekozen if _is_aardappelgerecht(g)) >= 1:
                return False
        if categorie == "zalm" and sum(1 for g in gekozen if str(g.get("categorie", "")).lower() == "zalm") >= 1:
            return False
        if categorie == "kabeljauw" and sum(1 for g in gekozen if str(g.get("categorie", "")).lower() == "kabeljauw") >= 1:
            return False
        return True

    # 1) Verplicht minimaal aantal vegetarische recepten.
    min_veg = int(instellingen.get("vegetarisch_per_week", config.MIN_VEGETARISCH))
    for r in vegetarisch:
        if len([g for g in gekozen if g.get("vegetarisch")]) >= min_veg:
            break
        if not is_toegestaan(r):
            continue
        gekozen.append(r)
        gebruikte_categorieen.append(r.get("categorie", ""))
    if len([g for g in gekozen if g.get("vegetarisch")]) < min_veg:
        waarschuwingen.append(
            "Niet genoeg vegetarische recepten beschikbaar voor de voorkeur."
        )

    # 2) Vul aan met variatie; favorieten winnen bij gelijke variatie-score.
    fav_voorrang = bool(instellingen.get("favorieten_voorrang", True))

    def variatie_score(recept: dict[str, Any]) -> int:
        """Lager = beter; straft categorieën die al vaak gekozen zijn."""
        return gebruikte_categorieen.count(recept.get("categorie", ""))

    while len(gekozen) < config.AANTAL_MAALTIJDEN:
        overige = [r for r in (vegetarisch + niet_veg)
                   if r not in gekozen and is_toegestaan(r)]
        if not overige:
            break
        overige.sort(key=lambda r: (variatie_score(r),
                                    0 if (fav_voorrang and is_fav(r)) else 1))
        beste = (variatie_score(overige[0]),
                 0 if (fav_voorrang and is_fav(overige[0])) else 1)
        kandidaten = [r for r in overige
                      if (variatie_score(r),
                          0 if (fav_voorrang and is_fav(r)) else 1) == beste]
        keuze = rng.choice(kandidaten)
        gekozen.append(keuze)
        gebruikte_categorieen.append(keuze.get("categorie", ""))

    if len(gekozen) < config.AANTAL_MAALTIJDEN:
        waarschuwingen.append(
            f"Slechts {len(gekozen)} van {config.AANTAL_MAALTIJDEN} maaltijden "
            "konden worden gevuld; voeg meer recepten toe."
        )

    # 3) Groentevalidatie + aanvulling, daarna schalen naar het gezin.
    doel_porties = config.gezinsporties(instellingen)
    resultaat = []
    for r in gekozen:
        verwerkt = _markeer_groente(r)
        if not verwerkt["voldeed_origineel"] and verwerkt["is_aangevuld"]:
            waarschuwingen.append(
                f"⚠️ '{verwerkt.get('naam')}' had te weinig groente en is "
                f"aangevuld tot {verwerkt['groente_per_persoon']} g/persoon."
            )
        verwerkt = schaal_recept(verwerkt, doel_porties)
        verwerkt["is_favoriet_bron"] = is_fav(r)
        resultaat.append(verwerkt)

    return resultaat, waarschuwingen
