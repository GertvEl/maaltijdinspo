"""
app.py
------
Maaltijdinspo — Streamlit-webapp (donker thema).

Start lokaal met:  streamlit run app.py

Pagina's:
  * Weekmenu      – genereer 7 maaltijden, kies er 3, exporteer boodschappenlijst
  * Favorieten    – opgeslagen favoriete recepten (inspiratiebron voor het menu)
  * Instellingen  – gezinsprofiel, voorkeuren, recepten beheren, scrapen
"""

from __future__ import annotations

import datetime

import streamlit as st

import config
from src import recepten as recepten_mod
from src import maaltijd_generator, boodschappenlijst, scraping, validatie, receptsites
from src import opslag as opslag_mod

# --------------------------------------------------------------------------
# Pagina-instellingen + donker thema (custom CSS bovenop config.toml)
# --------------------------------------------------------------------------
st.set_page_config(
    layout="wide",
    page_title=config.APP_NAAM,
    page_icon="🍽️",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .stApp { background-color: #0e1117; color: #fafafa; }
      .recept-kaart {
        background: #1c2330; border: 1px solid #2a3344; border-radius: 12px;
        padding: 16px; margin-bottom: 12px;
      }
      .groente-badge {
        background: #14532d; color: #d1fae5; padding: 2px 10px;
        border-radius: 999px; font-size: 0.85rem;
      }
      .bio-ja { color: #34d399; font-weight: 600; }
      .bio-nee { color: #9ca3af; }
      .bron { color: #60a5fa; font-size: 0.85rem; }
      /* Mobielvriendelijk: kaarten op smalle schermen volle breedte */
      @media (max-width: 640px) { .recept-kaart { padding: 12px; } }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------
# Sessiestatus
# --------------------------------------------------------------------------
if "weekmenu" not in st.session_state:
    st.session_state.weekmenu = recepten_mod.laad_selectie() or []
if "selectie" not in st.session_state:
    st.session_state.selectie = set()


def _toon_recept_kaart(recept: dict, index: int, selecteerbaar: bool = True) -> None:
    """Render één receptkaart met groentebadge, biologisch-status en knoppen."""
    naam = recept.get("naam", "Onbekend")
    groente = recept.get("groente_per_persoon", round(validatie.groente_gram_per_persoon(recept)))
    kooktijd = recept.get("kooktijd_min", "?")
    bio = any(i.get("biologisch") for i in recept.get("ingredienten", []))
    bron = recept.get("bron", "Lokaal")
    bron_url = recept.get("bron_url", "")

    with st.container():
        st.markdown('<div class="recept-kaart">', unsafe_allow_html=True)
        kol1, kol2 = st.columns([4, 1])
        with kol1:
            fav_badge = " ⭐" if recept.get("is_favoriet_bron") else ""
            st.markdown(f"### {naam}{fav_badge}")
            # Afbeelding van de bronwebsite (indien beschikbaar).
            afbeelding = str(recept.get("afbeelding_url", "")).strip()
            if afbeelding.startswith("http"):
                try:
                    st.image(afbeelding, width=320)
                except Exception:
                    pass  # kapotte afbeeldings-URL mag de kaart niet breken
            porties = recept.get("porties", "")
            porties_txt = f" &nbsp;·&nbsp; 👨‍👩‍👧 {porties} porties" if porties else ""
            bio_html = '<span class="bio-ja">✅ biologisch</span>' if bio else '<span class="bio-nee">❌ niet-bio</span>'
            bron_html = f'<a class="bron" href="{bron_url}" target="_blank">{bron}</a>' if bron_url else f'<span class="bron">{bron}</span>'
            st.markdown(
                f'⏱️ {kooktijd} min &nbsp;·&nbsp; '
                f'<span class="groente-badge">🥦 {groente} g groente/pers.</span>'
                f'{porties_txt} &nbsp;·&nbsp; '
                f'{bio_html} &nbsp;·&nbsp; {bron_html}',
                unsafe_allow_html=True,
            )
            if recept.get("is_aangevuld"):
                st.caption("⚠️ Automatisch aangevuld met extra groente om de norm te halen.")
        with kol2:
            is_fav = recepten_mod.is_favoriet(naam)
            ster = "⭐" if is_fav else "☆"
            if st.button(ster, key=f"fav_{index}_{naam}", help="Favoriet aan/uit"):
                recepten_mod.wissel_favoriet(recept)
                st.rerun()

        with st.expander("Bekijk recept"):
            st.markdown("**Ingrediënten**")
            for ing in recept.get("ingredienten", []):
                h = ing.get("hoeveelheid", "")
                e = ing.get("eenheid", "")
                mark = "🥦 " if ing.get("groente") or ing.get("categorie") == "groente" else ""
                hoeveelheid = f"{h} {e}".strip() if h else "naar smaak"
                st.markdown(f"- {mark}{ing.get('product','')} — {hoeveelheid}")
            if recept.get("stappen"):
                st.markdown("**Bereiding**")
                for i, stap in enumerate(recept["stappen"], 1):
                    st.markdown(f"{i}. {stap}")

        if selecteerbaar:
            gekozen = naam in st.session_state.selectie
            nieuw = st.checkbox(
                f"Kies '{naam}' voor deze week", value=gekozen, key=f"sel_{index}_{naam}"
            )
            if nieuw and not gekozen:
                if len(st.session_state.selectie) >= config.AANTAL_SELECTIE:
                    st.warning(f"Je kunt maximaal {config.AANTAL_SELECTIE} recepten kiezen.")
                else:
                    st.session_state.selectie.add(naam)
            elif not nieuw and gekozen:
                st.session_state.selectie.discard(naam)
        st.markdown("</div>", unsafe_allow_html=True)


MAANDEN_NL = ["", "januari", "februari", "maart", "april", "mei", "juni",
              "juli", "augustus", "september", "oktober", "november", "december"]


def volgende_week_titel() -> str:
    """Bijv. 'Week 25 (15–21 juni 2026)' — de eerstvolgende volledige week."""
    vandaag = datetime.date.today()
    maandag = vandaag + datetime.timedelta(days=(7 - vandaag.weekday()))
    zondag = maandag + datetime.timedelta(days=6)
    week = maandag.isocalendar().week
    if maandag.month == zondag.month:
        periode = f"{maandag.day}–{zondag.day} {MAANDEN_NL[zondag.month]} {zondag.year}"
    else:
        periode = (f"{maandag.day} {MAANDEN_NL[maandag.month]} – "
                   f"{zondag.day} {MAANDEN_NL[zondag.month]} {zondag.year}")
    return f"Week {week} ({periode})"


# --------------------------------------------------------------------------
# Pagina: Weekmenu
# --------------------------------------------------------------------------
def pagina_weekmenu() -> None:
    instellingen = recepten_mod.laad_instellingen()
    volw = int(instellingen.get("volwassenen", config.STANDAARD_VOLWASSENEN))
    kind = int(instellingen.get("kinderen", config.STANDAARD_KINDEREN))

    st.title(f"🍽️ {config.APP_NAAM} – {volgende_week_titel()}")
    st.caption(
        f"7 eenvoudige maaltijden (≤ 30 min, min. {config.GROENTE_MIN_PER_PERSOON} g "
        f"groente p.p.) voor {volw} volwassene(n) + {kind} kind(eren). "
        "⭐ Favorieten krijgen voorrang als inspiratie."
    )

    if st.button("🎲 Genereer 7 maaltijden voor volgende week", type="primary"):
        alle = recepten_mod.laad_recepten()
        # Neem ook gescrapete recepten mee in de pool (dedup op naam).
        bekende_namen = {r.get("naam", "").lower() for r in alle}
        for r in receptsites.laad_gescrapete_recepten():
            if r.get("naam", "").lower() not in bekende_namen:
                alle.append(r)
                bekende_namen.add(r.get("naam", "").lower())
        geschikt = recepten_mod.filter_op_voorkeuren(alle, instellingen)
        favoriete_namen = {f.get("naam", "") for f in recepten_mod.laad_favorieten()}
        menu, waarschuwingen = maaltijd_generator.genereer_weekmenu(
            geschikt, instellingen, favoriete_namen=favoriete_namen
        )
        st.session_state.weekmenu = menu
        st.session_state.selectie = set()
        recepten_mod.bewaar_selectie(menu)
        st.toast("✅ Nieuwe recepten gegenereerd! Selecteer 3 voor deze week.", icon="✅")
        for w in waarschuwingen:
            st.toast(w, icon="⚠️")

    menu = st.session_state.weekmenu
    if not menu:
        st.info("Nog geen weekmenu. Klik op de knop hierboven om te genereren.")
        return

    st.subheader(f"Weekmenu ({len(menu)} maaltijden)")
    st.write(f"Geselecteerd: **{len(st.session_state.selectie)} / {config.AANTAL_SELECTIE}**")

    for i, recept in enumerate(menu):
        _toon_recept_kaart(recept, i, selecteerbaar=True)

    st.divider()
    kol1, kol2 = st.columns(2)
    with kol1:
        if st.button("💾 Bevestig selectie"):
            if len(st.session_state.selectie) != config.AANTAL_SELECTIE:
                st.warning(f"Kies precies {config.AANTAL_SELECTIE} recepten.")
            else:
                gekozen = [r for r in menu if r.get("naam") in st.session_state.selectie]
                recepten_mod.bewaar_selectie(gekozen)
                st.toast("💾 Selectie opgeslagen!", icon="💾")
                st.success("Je 3 recepten zijn opgeslagen in geselecteerde_recepten.json.")

    with kol2:
        gekozen = [r for r in menu if r.get("naam") in st.session_state.selectie]
        if gekozen:
            lijst = boodschappenlijst.bouw_lijst(gekozen)
            csv = boodschappenlijst.naar_csv(lijst)
            st.toast("🛒 Boodschappenlijst klaar voor export!", icon="🛒")
            st.download_button(
                "🛒 Exporteer boodschappenlijst als CSV",
                data=csv,
                file_name="boodschappenlijst.csv",
                mime="text/csv",
            )
            with st.expander("Voorbeeld boodschappenlijst"):
                st.dataframe(lijst, use_container_width=True)
        else:
            st.button("🛒 Exporteer boodschappenlijst als CSV", disabled=True,
                      help="Kies eerst recepten en bevestig je selectie.")


# --------------------------------------------------------------------------
# Pagina: Favorieten
# --------------------------------------------------------------------------
def pagina_favorieten() -> None:
    st.title("⭐ Favorieten")
    favorieten = recepten_mod.laad_favorieten()
    if not favorieten:
        st.info("Je hebt nog geen favorieten. Klik op het sterretje bij een recept.")
        return
    for i, recept in enumerate(favorieten):
        _toon_recept_kaart(recept, f"fav{i}", selecteerbaar=False)
        if st.button(f"🗑️ Verwijder '{recept.get('naam')}'", key=f"del_fav_{i}"):
            recepten_mod.verwijder_favoriet(recept.get("naam"))
            st.rerun()


# --------------------------------------------------------------------------
# Pagina: Instellingen
# --------------------------------------------------------------------------
def pagina_instellingen() -> None:
    st.title("⚙️ Instellingen")
    instellingen = recepten_mod.laad_instellingen()

    st.subheader("Gezinsprofiel")
    kol_g1, kol_g2 = st.columns(2)
    with kol_g1:
        volw = st.number_input("Volwassenen", 1, 8,
                               int(instellingen.get("volwassenen", config.STANDAARD_VOLWASSENEN)))
    with kol_g2:
        kind = st.number_input("Kleine kinderen (tellen als halve portie)", 0, 8,
                               int(instellingen.get("kinderen", config.STANDAARD_KINDEREN)))
    st.caption(f"Recepten en boodschappenlijst worden geschaald naar "
               f"**{volw + kind * config.KIND_FACTOR:g} porties**.")

    st.subheader("Voorkeuren")
    kooktijd = st.slider("Max. kooktijd (min)", 10, config.KOOKTIJD_MAX,
                         int(instellingen.get("kooktijd_max", config.KOOKTIJD_MAX)))
    bio = st.checkbox("Voorkeur biologisch", value=instellingen.get("voorkeur_biologisch", True))
    veg = st.number_input("Vegetarische maaltijden per week", 0, 7,
                          int(instellingen.get("vegetarisch_per_week", 1)))
    fav_voorrang = st.checkbox(
        "⭐ Favorieten voorrang geven bij het genereren",
        value=instellingen.get("favorieten_voorrang", True),
    )
    cats = st.multiselect("Voorkeurscategorieën", config.TOEGESTANE_CATEGORIEEN,
                          default=instellingen.get("voorkeur_categorieen", config.TOEGESTANE_CATEGORIEEN))
    scraping_aan = st.checkbox(
        "Online scrapen toestaan (receptensites)",
        value=instellingen.get("scraping_aan", False),
        help="Standaard uit. De app werkt volledig offline op de lokale database.",
    )

    if st.button("💾 Voorkeuren opslaan"):
        instellingen.update({
            "volwassenen": int(volw), "kinderen": int(kind),
            "kooktijd_max": int(kooktijd),
            "voorkeur_biologisch": bio, "vegetarisch_per_week": int(veg),
            "favorieten_voorrang": fav_voorrang,
            "voorkeur_categorieen": cats, "scraping_aan": scraping_aan,
        })
        recepten_mod.bewaar_instellingen(instellingen)
        st.toast("💾 Voorkeuren opgeslagen!", icon="💾")

    st.divider()
    st.subheader("Recept handmatig toevoegen")
    with st.form("nieuw_recept"):
        naam = st.text_input("Naam")
        n_kol1, n_kol2, n_kol3 = st.columns(3)
        with n_kol1:
            categorie = st.selectbox("Categorie", config.TOEGESTANE_CATEGORIEEN)
        with n_kol2:
            kooktijd_n = st.number_input("Kooktijd (min)", 1, config.KOOKTIJD_MAX, 15)
        with n_kol3:
            porties_n = st.number_input("Porties", 1, 8, 2)
        vegetarisch_n = st.checkbox("Vegetarisch")
        groente_hoofd = st.checkbox("Groente is hoofdingrediënt (salade/soep)")
        st.caption("Voer ingrediënten in, één per regel: product; hoeveelheid; eenheid; categorie; groente(ja/nee)")
        ingredienten_tekst = st.text_area(
            "Ingrediënten",
            placeholder="broccoli; 250; g; groente; ja\nkipfilet; 250; g; vlees; nee",
        )
        verzenden = st.form_submit_button("Recept valideren en opslaan")

    if verzenden:
        ingredienten = []
        for regel in ingredienten_tekst.strip().splitlines():
            delen = [d.strip() for d in regel.split(";")]
            if len(delen) < 3:
                continue
            try:
                hoeveelheid = float(delen[1])
            except ValueError:
                hoeveelheid = 0
            ingredienten.append({
                "product": delen[0],
                "hoeveelheid": hoeveelheid,
                "eenheid": delen[2] if len(delen) > 2 else "",
                "categorie": delen[3] if len(delen) > 3 else "overig",
                "groente": (len(delen) > 4 and delen[4].lower() in {"ja", "true", "1"}),
            })
        recept = {
            "naam": naam, "categorie": categorie, "kooktijd_min": int(kooktijd_n),
            "porties": int(porties_n), "vegetarisch": vegetarisch_n,
            "groente_hoofdingredient": groente_hoofd, "ingredienten": ingredienten,
            "stappen": [], "bron": "Handmatig", "bron_url": "",
        }
        ok, fouten = recepten_mod.voeg_recept_toe(recept)
        if ok:
            st.toast("✅ Recept opgeslagen!", icon="✅")
            st.success(f"'{naam}' is toegevoegd.")
        else:
            for f in fouten:
                st.error(f)

    st.divider()
    st.subheader("Bestaande recepten verwijderen")
    alle = recepten_mod.laad_recepten()
    if alle:
        te_verwijderen = st.selectbox("Kies recept", [r["naam"] for r in alle])
        if st.button("🗑️ Verwijder gekozen recept"):
            recepten_mod.verwijder_recept(te_verwijderen)
            st.toast("🗑️ Recept verwijderd.", icon="🗑️")
            st.rerun()

    st.divider()
    st.subheader("Receptensites scrapen")
    st.caption(
        "Recepten worden opgehaald via schema.org Recipe-data (JSON-LD). "
        "Rate limit: max. 1 scrape-sessie per site per uur; robots.txt wordt "
        "gerespecteerd. Sites met 🔒 renderen via JavaScript en leveren met "
        "deze methode meestal geen overzicht op."
    )
    if not instellingen.get("scraping_aan"):
        st.info("Zet eerst 'Online scrapen toestaan' aan (bovenaan deze pagina).")
    else:
        # Overzicht van geconfigureerde sites met individuele scrape-knop.
        for i, site in enumerate(receptsites.SITE_CONFIGS):
            kol_s1, kol_s2 = st.columns([4, 1])
            with kol_s1:
                slot = " 🔒" if site.get("dynamisch") else ""
                st.markdown(f"**{site['naam']}**{slot}  \n`{site['listing_url'][:80]}`")
            with kol_s2:
                if st.button("Scrape", key=f"scrape_site_{i}"):
                    with st.spinner(f"{site['naam']} scrapen..."):
                        gevonden, status = receptsites.scrape_site(site)
                        geschikt = receptsites.filter_geschikt(gevonden)
                        nieuw = receptsites.bewaar_gescrapete_recepten(geschikt) if geschikt else 0
                    st.toast(status, icon="📥")
                    if nieuw:
                        st.toast(f"✅ {nieuw} nieuw(e) recept(en) toegevoegd!", icon="✅")

        if st.button("📥 Scrape alle sites", type="primary"):
            voortgang = st.progress(0.0, text="Bezig met scrapen...")
            meldingen: list[str] = []
            totaal_nieuw = 0
            n_sites = len(receptsites.SITE_CONFIGS)
            for i, site in enumerate(receptsites.SITE_CONFIGS):
                voortgang.progress((i + 1) / n_sites, text=f"{site['naam']}...")
                gevonden, status = receptsites.scrape_site(site)
                meldingen.append(status)
                geschikt = receptsites.filter_geschikt(gevonden)
                if geschikt:
                    totaal_nieuw += receptsites.bewaar_gescrapete_recepten(geschikt)
            voortgang.empty()
            st.toast(f"✅ Klaar: {totaal_nieuw} nieuw(e) recept(en) toegevoegd.", icon="✅")
            with st.expander("Scrape-log"):
                for m in meldingen:
                    st.markdown(f"- {m}")

        st.markdown("**Eén recept-URL importeren** (werkt ook voor 🔒-sites)")
        recept_url = st.text_input("Recept-URL", placeholder="https://www.lekkerensimpel.com/...")
        if st.button("➕ Importeer recept van URL"):
            if not validatie.valideer_url(recept_url):
                st.error("Ongeldige URL.")
            else:
                with st.spinner("Recept ophalen..."):
                    html = scraping._haal_op(recept_url.strip())
                    obj = receptsites._vind_recipe_jsonld(html) if html else None
                if obj is None:
                    st.error("Geen schema.org Recipe-data op deze pagina gevonden.")
                else:
                    recept = receptsites.converteer_jsonld_recept(obj, recept_url.strip())
                    n = receptsites.bewaar_gescrapete_recepten([recept])
                    if n:
                        st.toast(f"✅ '{recept['naam']}' geïmporteerd!", icon="✅")
                    else:
                        st.info("Dit recept was al geïmporteerd.")

    # Overzicht en beheer van gescrapete recepten.
    gescraped = receptsites.laad_gescrapete_recepten()
    if gescraped:
        st.markdown(f"**Gescrapete recepten ({len(gescraped)})**")
        with st.expander("Bekijk en beheer"):
            for i, r in enumerate(gescraped):
                gram = validatie.groente_gram_per_persoon(r)
                kol_g1, kol_g2 = st.columns([5, 1])
                with kol_g1:
                    st.markdown(
                        f"{r.get('naam')} — ⏱️ {r.get('kooktijd_min', '?')} min · "
                        f"🥦 {gram:.0f} g/pers · [{r.get('bron')}]({r.get('bron_url')})"
                    )
                with kol_g2:
                    if st.button("🗑️", key=f"del_scraped_{i}"):
                        overig = [x for x in gescraped if x.get("bron_url") != r.get("bron_url")]
                        opslag_mod.schrijf_json(receptsites.GESCRAPETE_RECEPTEN_BESTAND, overig)
                        st.rerun()

    st.divider()
    st.subheader("Extra receptensites (handmatig)")
    sites = instellingen.get("receptsites", list(config.STANDAARD_RECEPTSITES))
    nieuwe_site = st.text_input("Nieuwe site-URL toevoegen")
    if st.button("➕ Site toevoegen"):
        if validatie.valideer_url(nieuwe_site):
            sites.append(nieuwe_site.strip())
            instellingen["receptsites"] = sites
            recepten_mod.bewaar_instellingen(instellingen)
            st.toast("➕ Site toegevoegd.", icon="➕")
            st.rerun()
        else:
            st.error("Ongeldige URL (moet beginnen met https:// en geen spaties bevatten).")


# --------------------------------------------------------------------------
# Navigatie
# --------------------------------------------------------------------------
PAGINAS = {
    "🍽️ Weekmenu": pagina_weekmenu,
    "⭐ Favorieten": pagina_favorieten,
    "⚙️ Instellingen": pagina_instellingen,
}

keuze = st.sidebar.radio("Navigatie", list(PAGINAS.keys()))
st.sidebar.divider()
st.sidebar.caption("Maaltijdinspo · data wordt in de app-omgeving opgeslagen (JSON).")
PAGINAS[keuze]()
