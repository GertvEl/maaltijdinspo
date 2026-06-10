"""
scraping.py
-----------
Generieke, veilige scraping-helpers: rate limiting, robots.txt-respect,
nette headers en error handling. De site-specifieke receptlogica staat in
src/receptsites.py.

De gebruiker is zelf verantwoordelijk voor het naleven van de
gebruiksvoorwaarden van elke website.
"""

from __future__ import annotations

import json
import time
import urllib.robotparser
from typing import Any
from urllib.parse import urlparse

import config
from src import opslag

try:
    import requests
    from bs4 import BeautifulSoup
    _SCRAPING_BESCHIKBAAR = True
except ImportError:  # pragma: no cover - app werkt ook zonder deze libs (offline)
    _SCRAPING_BESCHIKBAAR = False


# --------------------------------------------------------------------------
# Rate limiting (persistente timestamps in data/rate_limits.json)
# --------------------------------------------------------------------------

def _rate_limits() -> dict[str, float]:
    data = opslag.laad_json(config.RATE_LIMIT_BESTAND, standaard={})
    return data if isinstance(data, dict) else {}


def mag_scrapen(sleutel: str, interval_sec: int) -> bool:
    """True als er sinds de laatste scrape genoeg tijd verstreken is."""
    limits = _rate_limits()
    laatste = float(limits.get(sleutel, 0))
    return (time.time() - laatste) >= interval_sec


def _registreer_scrape(sleutel: str) -> None:
    limits = _rate_limits()
    limits[sleutel] = time.time()
    opslag.schrijf_json(config.RATE_LIMIT_BESTAND, limits)


# --------------------------------------------------------------------------
# robots.txt
# --------------------------------------------------------------------------

def mag_volgens_robots(url: str) -> bool:
    """Controleer robots.txt voor onze user-agent. Bij twijfel: niet scrapen."""
    if not _SCRAPING_BESCHIKBAAR:
        return False
    try:
        delen = urlparse(url)
        robots_url = f"{delen.scheme}://{delen.netloc}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(config.USER_AGENT, url)
    except Exception:
        # Geen robots.txt leesbaar -> wees voorzichtig en sta het toe noch verbied
        # standaard. We kiezen hier voor "wel toegestaan" alleen als lezen lukte;
        # bij een fout geven we False terug (conservatief).
        return False


def _haal_op(url: str) -> str | None:
    """Haal een pagina op met nette headers en timeout. None bij fout."""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": config.USER_AGENT, "Accept-Language": "nl-NL"},
            timeout=config.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None


# --------------------------------------------------------------------------
# Recepten van derden (schema.org Recipe JSON-LD)
# --------------------------------------------------------------------------

def scrape_recept(url: str) -> tuple[dict[str, Any] | None, str]:
    """Scrape één recept-URL via schema.org Recipe JSON-LD.

    Rate limit: max. 1x per uur per domein. Respecteert robots.txt.
    """
    if not _SCRAPING_BESCHIKBAAR:
        return None, "Scraping-libraries niet beschikbaar."

    domein = urlparse(url).netloc
    sleutel = f"recept::{domein}"
    if not mag_scrapen(sleutel, config.RATE_LIMIT_RECEPTSITE):
        return None, f"Rate limit: {domein} is dit uur al benaderd."

    if not mag_volgens_robots(url):
        return None, f"robots.txt van {domein} staat dit niet toe."

    html = _haal_op(url)
    _registreer_scrape(sleutel)
    if html is None:
        return None, f"Ophalen van {url} mislukt."

    recept = _parse_recipe_jsonld(html, url)
    if recept is None:
        return None, "Geen schema.org Recipe-data op deze pagina gevonden."
    return recept, "Recept opgehaald."


def _parse_recipe_jsonld(html: str, bron_url: str) -> dict[str, Any] | None:
    """Haal een Recipe-object uit JSON-LD en zet het om naar ons formaat."""
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return None

    recipe_obj = None
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        # Data kan een lijst zijn of een @graph bevatten.
        kandidaten = data if isinstance(data, list) else data.get("@graph", [data])
        for item in kandidaten if isinstance(kandidaten, list) else [kandidaten]:
            if isinstance(item, dict) and "Recipe" in str(item.get("@type", "")):
                recipe_obj = item
                break
        if recipe_obj:
            break

    if not recipe_obj:
        return None

    naam = recipe_obj.get("name", "Onbekend recept")
    ingredienten_raw = recipe_obj.get("recipeIngredient", []) or []
    # We kunnen hoeveelheden niet betrouwbaar uit vrije tekst halen; daarom
    # markeren we ze als "naar smaak" (eenheid leeg). De gebruiker kan ze in
    # Instellingen aanvullen. Groentevalidatie vult zo nodig automatisch aan.
    ingredienten = []
    for tekst in ingredienten_raw[: config.MAX_INGREDIENTEN]:
        ingredienten.append({
            "product": str(tekst).strip(),
            "hoeveelheid": 0,
            "eenheid": "",
            "categorie": "overig",
            "groente": False,
        })

    afbeelding = recipe_obj.get("image")
    if isinstance(afbeelding, dict):
        afbeelding = afbeelding.get("url", "")
    elif isinstance(afbeelding, list) and afbeelding:
        afbeelding = afbeelding[0] if isinstance(afbeelding[0], str) else ""

    return {
        "naam": naam,
        "categorie": "overig",            # gebruiker categoriseert handmatig
        "kooktijd_min": 0,                # onbekend uit JSON-LD; gebruiker vult aan
        "porties": 2,
        "vegetarisch": False,
        "groente_hoofdingredient": False,
        "ingredienten": ingredienten,
        "stappen": [],
        "bron": urlparse(bron_url).netloc,
        "bron_url": bron_url,
        "afbeelding_url": afbeelding or "",
        "let_op": "Geïmporteerd via JSON-LD; controleer kooktijd, categorie en groentehoeveelheid.",
    }
