from pathlib import Path
import json

import config
from src.recepten import filter_op_voorkeuren

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "recepten.json"
OUTPUT_PATH = ROOT / "test_recepten_filter_output.txt"


def main() -> int:
    try:
        recepten = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"2) geldige JSON: nee ({exc})")
        return 1

    if not isinstance(recepten, list):
        print("2) geldige JSON: nee (root is geen lijst)")
        return 1

    instellingen = {
        "voorkeur_categorieen": list(config.TOEGESTANE_CATEGORIEEN),
        "kooktijd_max": config.KOOKTIJD_MAX,
    }

    filtered = filter_op_voorkeuren(recepten, instellingen)

    counts = {}
    for recept in recepten:
        categorie = str(recept.get("categorie", "")).lower()
        counts[categorie] = counts.get(categorie, 0) + 1

    lines = []
    lines.append(f"1) aantal recepten: {len(recepten)}")
    lines.append("2) geldige JSON: ja")
    lines.append("3) per categorie:")
    for categorie in config.TOEGESTANE_CATEGORIEEN:
        lines.append(f"   - {categorie}: {counts.get(categorie, 0)}")

    lines.append(f"4) filter_op_voorkeuren: {len(filtered)} van {len(recepten)} komen door")
    if len(filtered) == len(recepten):
        lines.append("   -> alle recepten komen door")
    else:
        gefaald = [r.get("naam") or r.get("id") or "onbekend" for r in recepten if r not in filtered]
        lines.append("   -> niet door filter:")
        for naam in gefaald:
            lines.append(f"      - {naam}")

    output = "\n".join(lines) + "\n"
    print(output, end="")
    OUTPUT_PATH.write_text(output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
