"""
config.py
---------
Centrale configuratie en constanten voor Maaltijdinspo. BEWUST GEEN
gevoelige data (geen API-keys, wachtwoorden of tokens).
"""

from __future__ import annotations

APP_NAAM = "Maaltijdinspo"

# --- Bestandsnamen (lokale opslag) ---
RECEPTEN_BESTAND = "recepten.json"
FAVORIETEN_BESTAND = "favorieten.json"
GESELECTEERD_BESTAND = "geselecteerde_recepten.json"
WEEKMENU_BESTAND = "weekmenu.json"
WEEKFAVORIETEN_BESTAND = "weekfavorieten.json"
INSTELLINGEN_BESTAND = "instellingen.json"
RATE_LIMIT_BESTAND = "rate_limits.json"

# --- Gezinsprofiel ---
# Een klein kind telt als een halve volwassen portie.
KIND_FACTOR = 0.5
STANDAARD_VOLWASSENEN = 2
STANDAARD_KINDEREN = 1

# --- Groentevalidatie ---
# Minimaal aantal gram groente per persoon per recept (vers of diepvries).
GROENTE_MIN_PER_PERSOON = 150
# Streefwaarde waarnaar we aanvullen als een recept te weinig groente heeft.
GROENTE_STREEF_PER_PERSOON = 200

# Groenten die gebruikt worden om recepten aan te vullen tot de streefwaarde.
AANVUL_GROENTEN = [
    {"product": "broccoli", "categorie": "groente"},
    {"product": "winterwortel", "categorie": "groente"},
    {"product": "spinazie (diepvries)", "categorie": "groente"},
    {"product": "haricots verts (diepvries)", "categorie": "groente"},
]

# --- Kooktijd ---
KOOKTIJD_MAX = 30          # harde grens (minuten)
KOOKTIJD_VOORKEUR = 15     # voorkeur (minuten)

# --- Eenvoud ---
MAX_INGREDIENTEN = 10      # "eenvoudig" = minder dan 10 ingrediënten

# --- Weekplanning ---
AANTAL_MAALTIJDEN = 7
MIN_VEGETARISCH = 1
AANTAL_SELECTIE = 3        # gebruiker kiest 3 van de 7

# --- Toegestane receptcategorieën (voorkeuren) ---
TOEGESTANE_CATEGORIEEN = [
    "kip", "rund", "zalm", "kabeljauw", "pasta", "vegetarisch",
]

# --- Rate limiting (in seconden) ---
RATE_LIMIT_RECEPTSITE = 60 * 60    # receptensites: max. 1x per uur per site

# --- Scraping ---
# Nette, herkenbare user-agent. Geen poging om een browser te vervalsen.
USER_AGENT = "Maaltijdinspo/1.0 (persoonlijk, niet-commercieel; respecteert robots.txt)"
REQUEST_TIMEOUT = 15  # seconden

# Standaard receptensites; de volledige scrape-configuratie per site staat
# in src/receptsites.py (SITE_CONFIGS). De gebruiker kan via Instellingen
# extra sites toevoegen (die worden generiek via JSON-LD gescraped).
STANDAARD_RECEPTSITES = [
    "https://www.euroma.nl/recepten",
    "https://www.voedzaamensnel.nl/category/hoofdgerecht/",
    "https://www.24kitchen.nl/recepten",
    "https://www.eefkooktzo.nl/hoofdgerechten/",
    "https://chickslovefood.com/moment-van-de-dag/diner/",
    "https://www.allesoveritaliaanseten.nl/italiaanse-recepten/",
    "https://www.foodiesmagazine.nl/zoeken/?post_types=recept&_sft_recipe-time=snel&_sft_recipe-course=hoofdgerecht",
    "https://www.voedingscentrum.nl/nl/gezonde-recepten.aspx",
    "https://www.lekkerensimpel.com/?s=&maaltijd=hoofdgerecht&gerecht=all",
    "https://miljuschka.nl/hoofdgerecht-recepten/?_gangen=diner&_bereidingstijd=0.00%2C30.00",
    "https://www.ah.nl/allerhande/recepten/snelle-recepten",
]

# --- Standaardinstellingen ---
STANDAARD_INSTELLINGEN = {
    "volwassenen": STANDAARD_VOLWASSENEN,
    "kinderen": STANDAARD_KINDEREN,
    "vegetarisch_per_week": MIN_VEGETARISCH,
    "kooktijd_max": KOOKTIJD_MAX,
    "voorkeur_biologisch": True,
    "voorkeur_categorieen": list(TOEGESTANE_CATEGORIEEN),
    "receptsites": list(STANDAARD_RECEPTSITES),
    "favorieten_voorrang": True,   # favorieten krijgen voorrang bij genereren
    "scraping_aan": False,  # standaard UIT: app draait offline tenzij gebruiker aanzet
}


def gezinsporties(instellingen: dict) -> float:
    """Aantal porties voor het gezin (kind = halve portie)."""
    volw = int(instellingen.get("volwassenen", STANDAARD_VOLWASSENEN))
    kind = int(instellingen.get("kinderen", STANDAARD_KINDEREN))
    return max(0.5, volw + kind * KIND_FACTOR)
