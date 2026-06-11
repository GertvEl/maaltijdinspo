# 🍽️ Maaltijdinspo

Een **veilige Streamlit-webapp** (donker thema) die wekelijks **7 eenvoudige maaltijden** voorstelt — met **bekende bereidingstijd van max. 30 minuten** en **minimaal 150 g groente per persoon** — geschaald naar jouw gezin (**2 volwassenen + 1 klein kind** als standaard). Je kiest er **3**, markeert **⭐ favorieten** (die als inspiratie voorrang krijgen bij het genereren) en exporteert een **boodschappenlijst als CSV**.

De app werkt **volledig offline** op een lokale receptendatabase. Het scrapen van receptensites is **optioneel** en standaard **uitgeschakeld**.

---

## Belangrijkste functies

- **Weekmenu met weeknummer en datums** (bijv. "Week 25 (15–21 juni 2026)") voor de eerstvolgende volledige week.
- **Gezinsschaling:** een klein kind telt als halve portie. Alle ingrediënthoeveelheden én de boodschappenlijst worden automatisch geschaald (standaard 2 + 1 kind = 2,5 porties; aanpasbaar in Instellingen).
- **Alleen recepten met een bekende bereidingstijd ≤ 30 min** doen mee. Recepten zonder kooktijd worden genegeerd.
- **Groentevalidatie:** minimaal 150 g groente per persoon (streefwaarde 200 g). Stuks-groenten tellen mee via een omrekentabel (1 courgette ≈ 300 g, 1 paprika ≈ 150 g, 1 ui ≈ 100 g, ...). Te magere recepten worden automatisch aangevuld; salades/soepen (groente als hoofdingrediënt) zijn uitgezonderd.
- **⭐ Favorieten als inspiratie:** favorieten krijgen voorrang bij het genereren van het weekmenu (uit te zetten in Instellingen), zodat het menu put uit wat jullie lekker vinden zonder elke week hetzelfde te zijn.
- **Recepten scrapen** van 11 Nederlandse receptensites via schema.org Recipe-data (JSON-LD), met Nederlandse ingrediënt-parser en groenteherkenning.
- **Boodschappenlijst-export (CSV)** met kolommen: `categorie, product, hoeveelheid, eenheid, biologisch, bron_recept` — gesorteerd op categorie, hoeveelheden geschaald naar het gezin.

> **Bewuste keuze:** de eerdere AH Bonus Folder-koppeling is verwijderd. Die folder is technisch niet betrouwbaar te scrapen (React-app met anti-bot), dus de planner werkt nu zonder Bonus-data.

---

## Lokaal installeren en starten

Vereist: **Python 3.10+**

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

De app opent op `http://localhost:8501`. Wil je zeker weten dat hij alléén lokaal bereikbaar is: `streamlit run app.py --server.address localhost`.

---

## 📱 Op iPhone en iPad draaien (zonder pc)

De app zelf is een website; om hem zonder je eigen pc te gebruiken moet hij ergens "wonen". De eenvoudigste gratis route is **Streamlit Community Cloud**:

1. **Maak een GitHub-account** op [github.com](https://github.com) (gratis).
2. **Maak een nieuw repository** (knop "New"), kies een naam (bijv. `maaltijdinspo`) en zet hem op **Private**.
3. **Upload de projectbestanden**: klik in je lege repository op "uploading an existing file" en sleep de complete inhoud van de uitgepakte zip erin (inclusief de mappen `src/`, `data/` en `.streamlit/`). Klik op "Commit changes".
4. Ga naar [share.streamlit.io](https://share.streamlit.io) en log in **met je GitHub-account**.
5. Klik **"Create app"** → kies je repository, branch `main`, main file `app.py` → **Deploy**.
6. Na 2–3 minuten krijg je een vast adres zoals `https://maaltijdinspo.streamlit.app`.
7. **Op je iPhone/iPad:** open dat adres in Safari → deelknop (vierkantje met pijl) → **"Zet op beginscherm"**. Maaltijdinspo staat nu als app-icoon tussen je andere apps en opent schermvullend.

**Eerlijke kanttekeningen bij deze route:**

- **Toegang:** de app draait dan op internet, niet meer alleen op localhost. Bij een private repository kun je in de app-instellingen van Streamlit Cloud de kijkers beperken tot specifieke e-mailadressen ("viewer access"). Er staat geen gevoelige data in de app, maar doe dit wel.
- **Opslag is niet permanent:** Streamlit Community Cloud bewaart de JSON-bestanden alleen zolang de app-container draait. Bij een herstart of nieuwe deploy worden **favorieten, instellingen en gescrapete recepten teruggezet** naar wat er in GitHub staat. De receptendatabase (`data/recepten.json`) blijft altijd — die zit in het repository. Wil je een favoriet permanent bewaren, voeg hem dan toe aan `data/favorieten.json` in GitHub (bestand openen → potloodje → plakken → commit). Voor casual gebruik is dit prima; permanente opslag zou een database vergen.
- **Slaapstand:** gratis apps gaan na een paar dagen inactiviteit slapen; de eerste keer openen duurt dan ±30 seconden.

*Alternatieven:* een Raspberry Pi thuis (volledige controle, data permanent, wel ~€60 en wat geknutsel) of een betaalde host als PythonAnywhere/Railway.

---

## 👨‍👩‍👧 Delen met je huishouden + permanente opslag

Iedereen met de app-link gebruikt **dezelfde app en dezelfde data** — delen werkt dus meteen. Het enige probleem op de gratis Streamlit-hosting: bij een herstart van de app (na een slaapje of update) gaat runtime-data zoals 📌 weekfavorieten verloren.

De oplossing zit ingebouwd: de app kan zijn weekfavorieten en ⭐ favorieten **opslaan in jouw eigen GitHub-repository** (op een aparte `data`-branch, zodat een save géén herstart van de app veroorzaakt). Eén keer instellen, ±5 minuten:

1. **Maak een toegangssleutel (token) aan op GitHub:** profielfoto → **Settings** → helemaal onderaan **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
   - Naam: `maaltijdinspo`
   - Expiration: kies bijv. 1 jaar
   - Repository access: **Only select repositories** → kies `maaltijdinspo`
   - Permissions → Repository permissions → **Contents: Read and write**
   - Klik **Generate token** en **kopieer de code** (begint met `github_pat_...`) — je ziet hem maar één keer!
2. **Geef de sleutel aan de app:** ga naar share.streamlit.io → je app → menu (⋮) → **Settings** → **Secrets** → plak dit (met jouw eigen token):

   ```toml
   [github]
   token = "github_pat_JOUW_TOKEN_HIER"
   repo = "GertvEl/maaltijdinspo"
   branch = "data"
   ```

3. Klik **Save**. De app herstart en op de 📌 Week-pagina staat nu "☁️ Gedeelde opslag actief".

**Belangrijk:** de token komt zo in de afgeschermde kluis van Streamlit terecht, **nooit in de code** — zet hem dus ook nooit in een bestand in je repository. Wijzigingen van huisgenoten verschijnen binnen een minuut bij de ander; als twee mensen exact tegelijk opslaan, wint de laatste.

---

## Wekelijks automatisch draaien (cron, alleen lokaal)

```cron
# Elke zondag om 08:00 Maaltijdinspo starten
0 8 * * 0 cd /pad/naar/maaltijdinspo && /pad/naar/.venv/bin/streamlit run app.py >> maaltijdinspo.log 2>&1
```

Op Streamlit Cloud is dit niet nodig: de app staat altijd klaar; je klikt zelf op "Genereer".

---

## Voorbeeld recept (`data/recepten.json`)

```json
{
  "naam": "Pasta Pesto met Kip",
  "categorie": "kip",
  "kooktijd_min": 15,
  "porties": 2,
  "vegetarisch": false,
  "groente_hoofdingredient": false,
  "ingredienten": [
    {"product": "broccoli", "hoeveelheid": 250, "eenheid": "g", "categorie": "groente", "groente": true, "biologisch": false},
    {"product": "kipfilet", "hoeveelheid": 250, "eenheid": "g", "categorie": "vlees", "groente": false, "biologisch": true}
  ],
  "stappen": ["Kook de pasta...", "Bak de kip..."],
  "bron": "Lokaal",
  "bron_url": "",
  "afbeelding_url": ""
}
```

`kooktijd_min` is **verplicht en moet 1–30 zijn**, anders doet het recept niet mee. Bij handmatig toevoegen via Instellingen wordt een recept met te weinig groente geweigerd met een duidelijke melding.

---

## CSV-export

Kolommen: `categorie, product, hoeveelheid, eenheid, biologisch, bron_recept`. Hoeveelheden zijn geschaald naar je gezinsprofiel. Open het bestand in Excel/Numbers en neem de producten over in je boodschappen-app naar keuze (supermarkt-apps ondersteunen geen CSV-import).

---

## Receptensites scrapen (optioneel)

Recepten worden opgehaald via **schema.org `Recipe` (JSON-LD)**: naam, kooktijd, porties, ingrediënten mét hoeveelheden ("200 gr broccoli" → 200 g groente ✅), stappen en afbeelding. Een Nederlandse parser herkent groenten, met uitzonderingen (paprika*poeder*, uien*soep* en tomaten*puree* tellen níet).

| Site | Listing scrapebaar? |
|---|---|
| Lekker en Simpel | ✅ |
| Voedzaam & Snel | ✅ |
| Euroma | ✅ |
| Eef Kookt Zo | ✅ |
| Chickslovefood | ✅ |
| Alles over Italiaans eten | ✅ |
| Voedingscentrum | ✅ |
| Miljuschka | ✅ (zonder facet-filters) |
| Foodies Magazine | 🔒 JavaScript |
| 24Kitchen | 🔒 JavaScript |
| AH Allerhande | 🔒 JavaScript + anti-bot |

Voor 🔒-sites: gebruik **"Importeer recept van URL"** in Instellingen (detailpagina's bevatten wél JSON-LD). Rate limit: 1 sessie per site per uur, 2 s pauze tussen requests, robots.txt wordt gerespecteerd. Of scrapen is toegestaan hangt af van de gebruiksvoorwaarden van elke site — dat is jouw verantwoordelijkheid. Let op: gescrapete recepten zonder herkenbare kooktijd doen **niet** mee in het weekmenu (jouw eis); importeer dan een ander recept of voeg het handmatig toe met kooktijd.

---

## Veiligheidsmaatregelen

- Geen gevoelige data in de code (geen API-keys of wachtwoorden).
- Inputvalidatie op alle invoer (recepten, instellingen, URL's), incl. de groentenorm.
- Rate limiting en robots.txt-respect bij scrapen; bij twijfel wordt níet gescraped.
- Error handling: mislukt scrapen → app draait gewoon door op de lokale database.
- Atomische lokale JSON-opslag (geen database).
- Lokaal draaien kan volledig afgeschermd (`--server.address localhost`); scrapen staat standaard uit.

---

## Projectstructuur

```
maaltijdinspo/
├── app.py                       # Streamlit-app (Weekmenu / Favorieten / Instellingen)
├── config.py                    # Constanten + gezinsprofiel (geen secrets)
├── requirements.txt
├── README.md
├── .streamlit/config.toml       # Donker thema
├── data/                        # Lokale opslag (JSON)
│   ├── recepten.json            # 16 gevalideerde recepten
│   ├── favorieten.json
│   ├── geselecteerde_recepten.json
│   ├── gescrapete_recepten.json
│   └── rate_limits.json
└── src/
    ├── opslag.py                # Atomische JSON-opslag
    ├── validatie.py             # Groente- en inputvalidatie + stuks→gram
    ├── recepten.py              # Laden/filteren/favorieten/selectie
    ├── receptsites.py           # 11 site-configs + NL ingrediënt-parser
    ├── maaltijd_generator.py    # 7 maaltijden, variatie, favorieten-voorrang, schaling
    ├── boodschappenlijst.py     # Lijst + CSV-export
    └── scraping.py              # Generieke helpers (rate limit, robots.txt)
```
