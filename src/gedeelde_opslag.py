"""
gedeelde_opslag.py
------------------
Gedeelde, permanente opslag voor het huishouden via GitHub.

Probleem: op Streamlit Community Cloud is het bestandssysteem tijdelijk —
bij elke herstart van de app verdwijnen lokaal geschreven JSON-bestanden.

Oplossing: als de gebruiker in Streamlit Cloud een GitHub-token instelt
(via "Secrets", dus NIET in de code), schrijft deze module de data naar een
aparte "data"-branch van het eigen repository. Die branch wordt door
Streamlit Cloud niet in de gaten gehouden, dus een save veroorzaakt géén
herstart van de app. Iedereen in het huishouden die de app-link gebruikt,
ziet dezelfde data.

Zonder token valt alles automatisch terug op lokale JSON-opslag (werkt
prima lokaal; op de gratis cloud is het dan sessie-geheugen).

Verwachte secrets (Streamlit Cloud -> app -> Settings -> Secrets):

    [github]
    token = "github_pat_..."          # fine-grained token, alleen dit repo
    repo = "GertvEl/maaltijdinspo"
    branch = "data"                    # optioneel; standaard "data"

Let op: bij gelijktijdig opslaan door twee gezinsleden wint de laatste
(last-write-wins). Voor een boodschappen-app is dat acceptabel.
"""

from __future__ import annotations

import base64
import json
import time
from typing import Any

from src import opslag

try:
    import requests
    _REQUESTS_OK = True
except ImportError:  # pragma: no cover
    _REQUESTS_OK = False

# Kleine leescache zodat we GitHub niet bij elke herrender bevragen.
_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 60  # seconden; wijzigingen van huisgenoten zie je dus binnen 1 min
_TIMEOUT = 10


def _config() -> dict[str, str] | None:
    """Lees de GitHub-instellingen uit Streamlit secrets (indien aanwezig)."""
    try:
        import streamlit as st
        gh = st.secrets["github"]
        token = str(gh["token"]).strip()
        repo = str(gh["repo"]).strip()
        if not token or not repo or "/" not in repo:
            return None
        return {"token": token, "repo": repo,
                "branch": str(gh.get("branch", "data")).strip() or "data"}
    except Exception:
        return None


def actief() -> bool:
    """True als gedeelde (GitHub-)opslag geconfigureerd en bruikbaar is."""
    return _REQUESTS_OK and _config() is not None


def _headers(cfg: dict[str, str]) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {cfg['token']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _contents_url(cfg: dict[str, str], bestand: str) -> str:
    return f"https://api.github.com/repos/{cfg['repo']}/contents/data/{bestand}"


def _zorg_voor_branch(cfg: dict[str, str]) -> bool:
    """Maak de data-branch aan als die nog niet bestaat (vanaf de default branch)."""
    basis = f"https://api.github.com/repos/{cfg['repo']}"
    try:
        r = requests.get(f"{basis}/git/ref/heads/{cfg['branch']}",
                         headers=_headers(cfg), timeout=_TIMEOUT)
        if r.status_code == 200:
            return True
        # Branch bestaat niet: pak de sha van de default branch en maak hem aan.
        repo_info = requests.get(basis, headers=_headers(cfg), timeout=_TIMEOUT)
        default = repo_info.json().get("default_branch", "main")
        ref = requests.get(f"{basis}/git/ref/heads/{default}",
                           headers=_headers(cfg), timeout=_TIMEOUT)
        sha = ref.json()["object"]["sha"]
        nieuw = requests.post(
            f"{basis}/git/refs", headers=_headers(cfg), timeout=_TIMEOUT,
            json={"ref": f"refs/heads/{cfg['branch']}", "sha": sha},
        )
        return nieuw.status_code in (200, 201)
    except Exception:
        return False


def laad(bestand: str, standaard: Any = None) -> Any:
    """Laad data: uit GitHub (met cache) als geconfigureerd, anders lokaal."""
    cfg = _config() if _REQUESTS_OK else None
    if cfg is None:
        return opslag.laad_json(bestand, standaard=standaard)

    nu = time.time()
    if bestand in _CACHE and nu - _CACHE[bestand][0] < _CACHE_TTL:
        return _CACHE[bestand][1]

    try:
        r = requests.get(_contents_url(cfg, bestand), headers=_headers(cfg),
                         params={"ref": cfg["branch"]}, timeout=_TIMEOUT)
        if r.status_code == 200:
            inhoud = base64.b64decode(r.json()["content"]).decode("utf-8")
            data = json.loads(inhoud)
            _CACHE[bestand] = (nu, data)
            return data
        if r.status_code == 404:
            # Bestand bestaat (nog) niet op de data-branch.
            data = standaard if standaard is not None else {}
            _CACHE[bestand] = (nu, data)
            return data
    except Exception:
        pass
    # GitHub onbereikbaar: val terug op de lokale kopie.
    return opslag.laad_json(bestand, standaard=standaard)


def schrijf(bestand: str, data: Any) -> bool:
    """Schrijf data weg: altijd lokaal (fallback) en, indien actief, naar GitHub.

    Geeft True terug als het wegschrijven naar de gedeelde opslag lukte
    (of als gedeelde opslag niet geconfigureerd is en lokaal volstond).
    """
    opslag.schrijf_json(bestand, data)
    _CACHE[bestand] = (time.time(), data)

    cfg = _config() if _REQUESTS_OK else None
    if cfg is None:
        return True

    try:
        if not _zorg_voor_branch(cfg):
            return False
        # Bestaande sha ophalen (vereist voor updates).
        sha = None
        r = requests.get(_contents_url(cfg, bestand), headers=_headers(cfg),
                         params={"ref": cfg["branch"]}, timeout=_TIMEOUT)
        if r.status_code == 200:
            sha = r.json().get("sha")

        payload: dict[str, Any] = {
            "message": f"Update {bestand} via Maaltijdinspo",
            "content": base64.b64encode(
                json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            ).decode("ascii"),
            "branch": cfg["branch"],
        }
        if sha:
            payload["sha"] = sha
        r = requests.put(_contents_url(cfg, bestand), headers=_headers(cfg),
                         json=payload, timeout=_TIMEOUT)
        return r.status_code in (200, 201)
    except Exception:
        return False
