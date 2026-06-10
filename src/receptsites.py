"""
receptsites.py
--------------
Per-site scraping van Nederlandse receptenwebsites.

Architectuur:
  1. LISTING: per site een overzichtspagina + een patroon om recept-links
     te herkennen in de HTML.
  2. DETAIL: universele parser voor schema.org "Recipe" JSON-LD (gebruikt
     door vrijwel alle WordPress-receptensites via plugins als WP Recipe
     Maker). Hieruit halen we naam, kooktijd, porties, ingrediënten (mét
     hoeveelheden), bereidingsstappen en afbeelding.
  3. VERRIJKING: Nederlandse ingrediënt-parser ("200 gr broccoli" ->
     product/hoeveelheid/eenheid), groenteherkenning, categorie-inferentie
     (kip/rund/zalm/kabeljauw/pasta/vegetarisch) en vegetarisch-detectie.

Rate limiting: max. 1 scrape-SESSIE per site per uur. Binnen een sessie
worden maximaal MAX_DETAILS_PER_SESSIE receptpagina's opgehaald met een
beleefde pauze ertussen. robots.txt wordt vooraf gecontroleerd.

Eerlijke kanttekening: sites gemarkeerd met dynamisch=True renderen hun
overzichtspagina via JavaScript; de listing levert daar met requests vaak
niets op (detailpagina's mét JSON-LD werken meestal wél via een directe
URL). Gebruik daarvoor Selenium of voeg recept-URL's handmatig toe.
"""

from __future__ import annotations

import re
import time
import unicodedata
from typing import Any
from urllib.parse import urljoin, urlparse

import config
from src import opslag, scraping, validatie

GESCRAPETE_RECEPTEN_BESTAND = "gescrapete_recepten.json"

# Beleefde pauze tussen requests binnen één scrape-sessie (seconden).
PAUZE_TUSSEN_REQUESTS = 2.0
# Max. aantal receptpagina's per site per sessie (houd het bescheiden).
MAX_DETAILS_PER_SESSIE = 5


# ==========================================================================
# Per-site configuratie
# ==========================================================================
# link_patroon: regex op de href om recept-detailpagina's te herkennen.
# uitsluiten:   padfragmenten die GEEN recepten zijn (categorieën, tags...).
SITE_CONFIGS: list[dict[str, Any]] = [
    {
        "naam": "Lekker en Simpel",
        "listing_url": "https://www.lekkerensimpel.com/?s=&maaltijd=hoofdgerecht&gerecht=all",
        "domein": "www.lekkerensimpel.com",
        # WP: recepten staan direct op /<slug>/
        "link_patroon": r"^https?://www\.lekkerensimpel\.com/[a-z0-9-]+/$",
        "uitsluiten": ["recepten", "hoofdgerechten", "themas", "tag", "category",
                       "ontbijt", "lunch", "over-ons", "contact", "privacy",
                       "wp-", "salades", "soepen", "dranken", "bakken"],
        "dynamisch": False,
    },
    {
        "naam": "Voedzaam & Snel",
        "listing_url": "https://www.voedzaamensnel.nl/category/hoofdgerecht/",
        "domein": "www.voedzaamensnel.nl",
        "link_patroon": r"^https?://www\.voedzaamensnel\.nl/(?:recept/)?[a-z0-9-]+/$",
        "uitsluiten": ["category", "tag", "author", "page", "over-", "contact",
                       "privacy", "wp-", "shop"],
        "dynamisch": False,
    },
    {
        "naam": "Euroma",
        "listing_url": "https://www.euroma.nl/recepten",
        "domein": "www.euroma.nl",
        "link_patroon": r"^https?://www\.euroma\.nl/recepten?/[a-z0-9-]+/?$",
        "uitsluiten": [],
        "dynamisch": False,
    },
    {
        "naam": "Eef Kookt Zo",
        "listing_url": "https://www.eefkooktzo.nl/hoofdgerechten/",
        "domein": "www.eefkooktzo.nl",
        "link_patroon": r"^https?://www\.eefkooktzo\.nl/[a-z0-9-]+/$",
        "uitsluiten": ["hoofdgerechten", "category", "tag", "over-", "contact",
                       "privacy", "wp-", "kookboek", "shop", "recepten"],
        "dynamisch": False,
    },
    {
        "naam": "Chickslovefood",
        "listing_url": "https://chickslovefood.com/moment-van-de-dag/diner/",
        "domein": "chickslovefood.com",
        "link_patroon": r"^https?://chickslovefood\.com/recept/[a-z0-9-]+/?$",
        "uitsluiten": ["moment-van-de-dag", "category", "tag", "wp-"],
        "dynamisch": False,
    },
    {
        "naam": "Alles over Italiaans eten",
        "listing_url": "https://www.allesoveritaliaanseten.nl/italiaanse-recepten/",
        "domein": "www.allesoveritaliaanseten.nl",
        "link_patroon": r"^https?://www\.allesoveritaliaanseten\.nl/[a-z0-9-]+/$",
        "uitsluiten": ["italiaanse-recepten", "category", "tag", "over-",
                       "contact", "privacy", "wp-"],
        "dynamisch": False,
    },
    {
        "naam": "Foodies Magazine",
        "listing_url": ("https://www.foodiesmagazine.nl/zoeken/?post_types=recept"
                        "&_sft_recipe-time=snel&_sft_recipe-course=hoofdgerecht"),
        "domein": "www.foodiesmagazine.nl",
        "link_patroon": r"^https?://www\.foodiesmagazine\.nl/recept/[a-z0-9-]+/?$",
        "uitsluiten": ["zoeken"],
        # Zoekpagina gebruikt FacetWP (JavaScript-filtering); listing kan
        # leeg of ongefilterd terugkomen met requests.
        "dynamisch": True,
    },
    {
        "naam": "Voedingscentrum",
        "listing_url": "https://www.voedingscentrum.nl/nl/gezonde-recepten.aspx",
        "domein": "www.voedingscentrum.nl",
        "link_patroon": r"^https?://www\.voedingscentrum\.nl/recepten/gezond-recept/[a-z0-9-]+\.aspx$",
        "uitsluiten": [],
        "dynamisch": False,
    },
    {
        "naam": "24Kitchen",
        "listing_url": "https://www.24kitchen.nl/recepten",
        "domein": "www.24kitchen.nl",
        "link_patroon": r"^https?://www\.24kitchen\.nl/recepten/[a-z0-9-]+/?$",
        "uitsluiten": [],
        # React-app: overzicht rendert client-side; vrijwel zeker Selenium nodig.
        "dynamisch": True,
    },
    {
        "naam": "Miljuschka",
        "listing_url": ("https://miljuschka.nl/hoofdgerecht-recepten/"
                        "?_gangen=diner&_bereidingstijd=0.00%2C30.00"),
        "domein": "miljuschka.nl",
        "link_patroon": r"^https?://miljuschka\.nl/[a-z0-9-]+/$",
        "uitsluiten": ["hoofdgerecht-recepten", "category", "tag", "over-",
                       "contact", "privacy", "wp-", "shop", "recepten"],
        # Facet-filters zijn JS; de basislijst rendert vaak wel server-side.
        "dynamisch": False,
    },
    {
        "naam": "AH Allerhande",
        "listing_url": "https://www.ah.nl/allerhande/recepten/snelle-recepten",
        "domein": "www.ah.nl",
        "link_patroon": r"^https?://www\.ah\.nl/allerhande/recept/R-R\d+/[a-z0-9-]+$",
        "uitsluiten": [],
        # ah.nl is een React-app met anti-bot; listing rendert client-side.
        "dynamisch": True,
    },
]


# ==========================================================================
# Nederlandse ingrediënt-parser
# ==========================================================================

# Korte/ambigue groentewoorden: alléén matchen als los woord (woordgrens),
# anders matcht "ui" per ongeluk in "kr-ui-denroomkaas".
GROENTE_WOORDEN_KORT = {
    "ui", "uien", "sla", "prei", "mais", "maïs", "erwten", "kool", "tomaat",
    "wortel", "biet", "bietjes", "venkel", "paksoi", "witlof", "radijs",
    "selderij", "asperges", "komkommer", "pompoen", "andijvie", "spruitjes",
    "aubergine", "paprika", "courgette", "champignon", "champignons",
}
# Langere, ondubbelzinnige groentewoorden: substring-match is veilig
# (vangt ook samenstellingen als "cherrytomaatjes", "wokgroente").
GROENTE_WOORDEN_LANG = {
    "broccoli", "bloemkool", "spinazie", "boerenkool", "winterpeen",
    "winterwortel", "cherrytoma", "tomaten", "sperziebonen", "haricots",
    "snijbonen", "doperwten", "ijsbergsla", "veldsla", "rucola",
    "paddenstoelen", "bosui", "sjalot", "zoete aardappel", "bleekselderij",
    "koolrabi", "rode kool", "witte kool", "spitskool", "chinese kool",
    "soepgroente", "wokgroente", "roerbakgroente", "raapstelen", "postelein",
    "snijbiet", "rode biet", "knolselderij", "pastinaak", "tuinbonen",
    "edamame", "courgett", "auberg",
}
# Als het product een van deze woorden bevat, is het GEEN (verse) groente,
# ook al komt er een groentenaam in voor (paprikaPOEDER, uienSOEP, etc.).
GROENTE_UITSLUITEN = {
    "poeder", "kruiden", "bouillon", "saus", "chips", "soep", "pasta",
    "olie", "azijn", "siroop", "sap", "puree", "ketchup", "passata",
}

# Vlees/vis-woorden voor categorie- en vegetarisch-detectie.
CATEGORIE_WOORDEN = {
    "kip": {"kip", "kipfilet", "kipdij", "kipdijfilet", "kipgehakt", "drumstick", "kippendij"},
    "rund": {"rund", "rundergehakt", "biefstuk", "runderlap", "entrecote", "sucade", "ossenhaas", "gehakt"},
    "zalm": {"zalm", "zalmfilet", "gerookte zalm"},
    "kabeljauw": {"kabeljauw", "kabeljauwfilet", "kabeljauwhaas"},
}
OVERIG_VLEES_VIS = {
    "varken", "spek", "spekjes", "ham", "worst", "chorizo", "salami", "bacon",
    "lam", "kalkoen", "eend", "tonijn", "garnalen", "garnaal", "vis", "forel",
    "makreel", "ansjovis", "mosselen", "kibbeling", "pangasius", "tilapia",
    "schelvis", "koolvis", "heek", "scholfilet", "schol",
}
PASTA_WOORDEN = {
    "pasta", "spaghetti", "penne", "tagliatelle", "fusilli", "macaroni",
    "lasagne", "linguine", "orzo", "rigatoni", "farfalle", "gnocchi", "ravioli",
}

# Eenheden-normalisatie.
EENHEID_MAP = {
    "g": "g", "gr": "g", "gram": "g",
    "kg": "kg", "kilo": "kg", "kilogram": "kg",
    "ml": "ml", "milliliter": "ml",
    "l": "l", "liter": "l",
    "el": "el", "eetlepel": "el", "eetlepels": "el",
    "tl": "tl", "theelepel": "tl", "theelepels": "tl",
    "stuk": "stuk", "stuks": "stuk", "st": "stuk",
    "teen": "teen", "tenen": "teen", "teentje": "teen", "teentjes": "teen",
    "snuf": "snuf", "snufje": "snuf",
    "blik": "blik", "blikje": "blik", "pak": "pak", "pakje": "pak",
    "zak": "zak", "zakje": "zak", "bos": "bos", "bosje": "bos",
    "plak": "plak", "plakjes": "plak", "plakje": "plak",
}

_INGREDIENT_RE = re.compile(
    r"^\s*(?:ca\.?\s*)?(\d+(?:[.,]\d+)?)"              # hoeveelheid
    r"(?:\s*[-–]\s*\d+(?:[.,]\d+)?)?\s*"               # optioneel bereik (5-6)
    r"(?:([a-zA-Z]+)\.?\s+)?"                          # optionele eenheid
    r"(.+?)\s*$"                                       # product
)


def _normaliseer(tekst: str) -> str:
    """Lowercase + accenten strippen voor robuuste woordvergelijking."""
    tekst = unicodedata.normalize("NFKD", tekst)
    return "".join(c for c in tekst if not unicodedata.combining(c)).lower()


def is_groente_tekst(product: str) -> bool:
    """Herken of een productomschrijving een (verse/diepvries) groente is."""
    p = _normaliseer(product)
    # Uitsluitingen eerst: paprikaPOEDER, uienSOEP, knoflookOLIE, etc.
    if any(u in p for u in GROENTE_UITSLUITEN):
        return False
    # Lange, ondubbelzinnige woorden: substring (vangt samenstellingen).
    if any(w in p for w in GROENTE_WOORDEN_LANG):
        return True
    # Korte woorden: alleen als los woord, met optionele verkleinings-/
    # meervoudsuitgang ("uitje", "tomaatjes", "worteltjes").
    woorden = re.findall(r"[a-z]+", p)
    for w in woorden:
        for kort in GROENTE_WOORDEN_KORT:
            basis = _normaliseer(kort)
            if w == basis or w in {basis + "tje", basis + "tjes",
                                   basis + "je", basis + "jes", basis + "en"}:
                return True
    return False


def parse_ingredient(tekst: str) -> dict[str, Any]:
    """Parse een Nederlandse ingrediëntregel naar ons formaat.

    Voorbeelden:
      "200 gr broccoli"        -> 200 g broccoli (groente)
      "2 el olijfolie"         -> 2 el olijfolie
      "1 ui"                   -> 1 stuk ui (groente)
      "zout en peper"          -> naar smaak
      "500 gram kipfilet"      -> 500 g kipfilet
    """
    tekst = str(tekst).strip()
    m = _INGREDIENT_RE.match(tekst)

    hoeveelheid: float = 0
    eenheid = ""
    product = tekst

    if m:
        try:
            hoeveelheid = float(m.group(1).replace(",", "."))
        except ValueError:
            hoeveelheid = 0
        ruwe_eenheid = (m.group(2) or "").lower()
        rest = m.group(3).strip()
        if ruwe_eenheid in EENHEID_MAP:
            eenheid = EENHEID_MAP[ruwe_eenheid]
            product = rest
        else:
            # "2 uien" -> eenheid 'stuk', product '(ruwe_eenheid + rest)'
            eenheid = "stuk" if hoeveelheid else ""
            product = f"{ruwe_eenheid} {rest}".strip()

    # kg/l omrekenen naar g/ml zodat de groentevalidatie kan rekenen.
    if eenheid == "kg":
        hoeveelheid, eenheid = hoeveelheid * 1000, "g"
    elif eenheid == "l":
        hoeveelheid, eenheid = hoeveelheid * 1000, "ml"

    groente = is_groente_tekst(product)
    categorie = "groente" if groente else _infereer_ingredient_categorie(product)

    return {
        "product": product,
        "hoeveelheid": int(hoeveelheid) if float(hoeveelheid).is_integer() else hoeveelheid,
        "eenheid": eenheid,
        "categorie": categorie,
        "groente": groente,
        "biologisch": "biologisch" in _normaliseer(product),
    }


def _infereer_ingredient_categorie(product: str) -> str:
    p = _normaliseer(product)
    for cat, woorden in CATEGORIE_WOORDEN.items():
        if any(w in p for w in woorden):
            return "vlees" if cat in {"kip", "rund"} else "vis"
    if any(w in p for w in OVERIG_VLEES_VIS):
        return "vlees"
    if any(w in p for w in PASTA_WOORDEN):
        return "pasta"
    if any(w in p for w in ("kaas", "melk", "room", "yoghurt", "boter", "creme fraiche", "crème")):
        return "zuivel"
    if any(w in p for w in ("saus", "passata", "pesto", "ketjap", "sojasaus", "bouillon")):
        return "saus"
    return "overig"


# ==========================================================================
# Recept-inferentie (categorie, vegetarisch, kooktijd)
# ==========================================================================

def _infereer_recept_categorie(naam: str, ingredienten: list[dict]) -> tuple[str, bool]:
    """Bepaal (categorie, vegetarisch) op basis van naam + ingrediënten."""
    tekst = _normaliseer(naam) + " " + " ".join(
        _normaliseer(i.get("product", "")) for i in ingredienten
    )
    for cat in ("kip", "rund", "zalm", "kabeljauw"):
        if any(w in tekst for w in CATEGORIE_WOORDEN[cat]):
            return cat, False
    bevat_vlees_vis = any(w in tekst for w in OVERIG_VLEES_VIS)
    if any(w in tekst for w in PASTA_WOORDEN):
        return "pasta", not bevat_vlees_vis
    return "vegetarisch" if not bevat_vlees_vis else "rund", not bevat_vlees_vis


_DUUR_RE = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?", re.IGNORECASE)


def parse_iso_duur(waarde: Any) -> int:
    """ISO-8601 duur (PT25M / PT1H10M) -> minuten. 0 bij onbekend."""
    if isinstance(waarde, (int, float)):
        return int(waarde)
    m = _DUUR_RE.match(str(waarde or ""))
    if not m:
        return 0
    uren = int(m.group(1) or 0)
    minuten = int(m.group(2) or 0)
    return uren * 60 + minuten


def _parse_porties(waarde: Any) -> int:
    if isinstance(waarde, list) and waarde:
        waarde = waarde[0]
    m = re.search(r"\d+", str(waarde or ""))
    return max(1, int(m.group())) if m else 2


def _parse_stappen(instructies: Any) -> list[str]:
    """schema.org recipeInstructions -> lijst van stappen (tekst)."""
    stappen: list[str] = []
    if isinstance(instructies, str):
        return [s.strip() for s in instructies.split("\n") if s.strip()]
    if isinstance(instructies, list):
        for item in instructies:
            if isinstance(item, str):
                stappen.append(item.strip())
            elif isinstance(item, dict):
                if item.get("@type") == "HowToSection":
                    stappen.extend(_parse_stappen(item.get("itemListElement", [])))
                else:
                    tekst = item.get("text") or item.get("name") or ""
                    if tekst:
                        stappen.append(str(tekst).strip())
    return stappen


def converteer_jsonld_recept(recipe_obj: dict[str, Any], bron_url: str) -> dict[str, Any]:
    """Zet een schema.org Recipe-object om naar het app-receptformaat."""
    naam = str(recipe_obj.get("name", "Onbekend recept")).strip()

    ingredienten = [
        parse_ingredient(t)
        for t in (recipe_obj.get("recipeIngredient") or [])
        if str(t).strip()
    ]

    kooktijd = parse_iso_duur(recipe_obj.get("totalTime")) or (
        parse_iso_duur(recipe_obj.get("prepTime"))
        + parse_iso_duur(recipe_obj.get("cookTime"))
    )

    afbeelding = recipe_obj.get("image")
    if isinstance(afbeelding, dict):
        afbeelding = afbeelding.get("url", "")
    elif isinstance(afbeelding, list) and afbeelding:
        eerste = afbeelding[0]
        afbeelding = eerste.get("url", "") if isinstance(eerste, dict) else str(eerste)

    categorie, vegetarisch = _infereer_recept_categorie(naam, ingredienten)

    return {
        "naam": naam,
        "categorie": categorie,
        "kooktijd_min": kooktijd,
        "porties": _parse_porties(recipe_obj.get("recipeYield")),
        "vegetarisch": vegetarisch,
        "groente_hoofdingredient": False,
        "ingredienten": ingredienten,
        "stappen": _parse_stappen(recipe_obj.get("recipeInstructions")),
        "bron": urlparse(bron_url).netloc.replace("www.", ""),
        "bron_url": bron_url,
        "afbeelding_url": str(afbeelding or ""),
    }


# ==========================================================================
# Listing-pagina: recept-links extraheren
# ==========================================================================

def extraheer_recept_links(html: str, site: dict[str, Any]) -> list[str]:
    """Vind recept-detail-URL's op een overzichtspagina volgens de site-config."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    patroon = re.compile(site["link_patroon"])
    uitsluiten = site.get("uitsluiten", [])
    basis = f"https://{site['domein']}/"

    links: list[str] = []
    gezien: set[str] = set()
    try:
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            url = urljoin(basis, a["href"]).split("#")[0].split("?")[0]
            if url in gezien:
                continue
            gezien.add(url)
            if not patroon.match(url):
                continue
            pad = urlparse(url).path.lower()
            if any(u in pad for u in uitsluiten):
                continue
            links.append(url)
    except Exception:
        return []
    return links


# ==========================================================================
# Scrape-sessie per site
# ==========================================================================

def scrape_site(site: dict[str, Any], max_recepten: int = MAX_DETAILS_PER_SESSIE,
                forceer: bool = False) -> tuple[list[dict[str, Any]], str]:
    """Voer één scrape-sessie uit voor een site.

    Rate limit: max. 1 sessie per site per uur. Binnen de sessie worden
    listing + max. `max_recepten` detailpagina's opgehaald met pauzes.
    """
    if not scraping._SCRAPING_BESCHIKBAAR:
        return [], "Scraping-libraries (requests/bs4) niet geïnstalleerd."

    sleutel = f"site::{site['domein']}"
    if not forceer and not scraping.mag_scrapen(sleutel, config.RATE_LIMIT_RECEPTSITE):
        return [], f"Rate limit: {site['naam']} is dit uur al gescraped."

    if not scraping.mag_volgens_robots(site["listing_url"]):
        return [], f"robots.txt van {site['naam']} staat dit niet toe (overgeslagen)."

    scraping._registreer_scrape(sleutel)

    html = scraping._haal_op(site["listing_url"])
    if html is None:
        return [], f"Overzichtspagina van {site['naam']} niet bereikbaar."

    links = extraheer_recept_links(html, site)
    if not links:
        hint = (" Deze site rendert via JavaScript; gebruik Selenium of voeg "
                "recept-URL's handmatig toe." if site.get("dynamisch") else "")
        return [], f"Geen recept-links gevonden op {site['naam']}.{hint}"

    recepten: list[dict[str, Any]] = []
    fouten = 0
    for url in links[:max_recepten]:
        time.sleep(PAUZE_TUSSEN_REQUESTS)  # beleefd: niet hameren op de server
        detail_html = scraping._haal_op(url)
        if detail_html is None:
            fouten += 1
            continue
        recipe_obj = _vind_recipe_jsonld(detail_html)
        if recipe_obj is None:
            fouten += 1
            continue
        recepten.append(converteer_jsonld_recept(recipe_obj, url))

    status = (f"{site['naam']}: {len(recepten)} recept(en) opgehaald "
              f"({len(links)} links gevonden, {fouten} zonder bruikbare data).")
    return recepten, status


def _vind_recipe_jsonld(html: str) -> dict[str, Any] | None:
    """Vind het eerste schema.org Recipe-object in de JSON-LD van een pagina."""
    import json
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return None

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        kandidaten: list[Any] = []
        if isinstance(data, list):
            kandidaten = data
        elif isinstance(data, dict):
            kandidaten = data.get("@graph", [data])
            if not isinstance(kandidaten, list):
                kandidaten = [kandidaten]
        for item in kandidaten:
            if isinstance(item, dict) and "Recipe" in str(item.get("@type", "")):
                return item
    return None


# ==========================================================================
# Filteren + opslaan van gescrapete recepten
# ==========================================================================

def filter_geschikt(recepten: list[dict[str, Any]],
                    kooktijd_max: int = config.KOOKTIJD_MAX) -> list[dict[str, Any]]:
    """Houd alleen recepten die aan de basisvoorwaarden (kunnen) voldoen.

    - Kooktijd bekend en <= max.
    - Minder dan MAX_INGREDIENTEN ingrediënten (eenvoud).
    - Groente aanwezig of aanvulbaar (de generator vult later aan); recepten
      ZONDER enige geparseerde gram-hoeveelheid laten we toe maar markeren we.
    """
    geschikt = []
    for r in recepten:
        if not (0 < r.get("kooktijd_min", 0) <= kooktijd_max):
            continue
        if len(r.get("ingredienten", [])) >= config.MAX_INGREDIENTEN:
            continue
        r["groente_per_persoon_geparsed"] = round(validatie.groente_gram_per_persoon(r))
        geschikt.append(r)
    return geschikt


def laad_gescrapete_recepten() -> list[dict[str, Any]]:
    data = opslag.laad_json(GESCRAPETE_RECEPTEN_BESTAND, standaard=[])
    return data if isinstance(data, list) else []


def bewaar_gescrapete_recepten(nieuw: list[dict[str, Any]]) -> int:
    """Voeg nieuwe recepten toe aan de gescrapete cache (dedup op bron_url)."""
    bestaand = laad_gescrapete_recepten()
    bekende_urls = {r.get("bron_url") for r in bestaand}
    toegevoegd = 0
    for r in nieuw:
        if r.get("bron_url") not in bekende_urls:
            bestaand.append(r)
            bekende_urls.add(r.get("bron_url"))
            toegevoegd += 1
    opslag.schrijf_json(GESCRAPETE_RECEPTEN_BESTAND, bestaand)
    return toegevoegd


def scrape_alle_sites(forceer: bool = False) -> tuple[int, list[str]]:
    """Scrape alle geconfigureerde sites. Geeft (aantal_nieuw, statusmeldingen)."""
    meldingen: list[str] = []
    alle_nieuw: list[dict[str, Any]] = []
    for site in SITE_CONFIGS:
        recepten, status = scrape_site(site, forceer=forceer)
        meldingen.append(status)
        alle_nieuw.extend(filter_geschikt(recepten))
    toegevoegd = bewaar_gescrapete_recepten(alle_nieuw) if alle_nieuw else 0
    return toegevoegd, meldingen
