#!/usr/bin/env python3
"""Hlídá nové produkty ve feedech MIJ a HobbyChef.

Nový produkt = kód z feedu, který není v Shoptetu (shoptet_reference.json)
a zároveň ho jsme ještě neoznámili (known_unmatched.json).

Při prvním běhu (soubor known_unmatched.json neexistuje) se současný stav
jen uloží jako výchozí a nic se neoznamuje.
Když jsou nové položky, zapíše Markdown do $NEW_PRODUCTS_MD (jinak soubor nevznikne)
a aktualizuje known_unmatched.json. Issue + commit řeší workflow.
"""
import csv
import json
import os
import xml.etree.ElementTree as ET

OUT_DIR = os.environ.get("OUT_DIR", "public")
STATE_PATH = os.environ.get("STATE_PATH", "known_unmatched.json")
REPORT_PATH = os.environ.get("NEW_PRODUCTS_MD", "new_products.md")
REFERENCE_PATH = os.environ.get("REFERENCE_PATH", "shoptet_reference.json")


def mij_unmatched():
    path = os.path.join(OUT_DIR, "unmatched_products.csv")
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter=";"):
            out[row["mijeurope_code"]] = (row["name"], row["stock"], row["mijeurope_ean"])
    return out


def hobbychef_unmatched(known_codes):
    path = os.path.join(OUT_DIR, "stock_import_hobbychef.xml")
    out = {}
    if not os.path.exists(path):
        return out
    for item in ET.parse(path).getroot().findall("SHOPITEM"):
        code = (item.findtext("CODE") or "").strip()
        if code and code not in known_codes:
            out[code] = ("", item.findtext("STOCK/AMOUNT") or "", "")
    return out


def table(rows):
    lines = ["| Kód | Název | Sklad | EAN |", "|---|---|---|---|"]
    for code, (name, stock, ean) in sorted(rows.items()):
        lines.append(f"| `{code}` | {name} | {stock} | {ean} |")
    return "\n".join(lines)


def main():
    with open(REFERENCE_PATH, encoding="utf-8") as f:
        known_codes = set(json.load(f)["codes"])

    current = {"mij": mij_unmatched(), "hobbychef": hobbychef_unmatched(known_codes)}

    if not os.path.exists(STATE_PATH):
        state = {k: sorted(v) for k, v in current.items()}
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
        print("První běh: uložen výchozí stav, nic se neoznamuje.")
        return

    with open(STATE_PATH, encoding="utf-8") as f:
        state = json.load(f)

    new = {}
    for src, rows in current.items():
        seen = set(state.get(src, []))
        fresh = {c: v for c, v in rows.items() if c not in seen}
        if fresh:
            new[src] = fresh

    if not new:
        print("Žádné nové produkty ve feedech.")
        return

    titles = {"mij": "MIJ (mijeurope.com)", "hobbychef": "HobbyChef (Yaxell, Hasegawa, Naniwa)"}
    parts = [
        "Ve feedech jsou kódy, které nejsou v Shoptetu (`shoptet_reference.json`). "
        "Mohou to být nové produkty, nebo administrativní řádky (Paleta, Dobírka, Box). "
        "Jejich sklad se nesynchronizuje, dokud je nezaložíte v Shoptetu a neobnovíte referenci.\n"
    ]
    for src, rows in new.items():
        parts.append(f"### {titles[src]} – {len(rows)}\n\n{table(rows)}\n")
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))

    for src, rows in new.items():
        state[src] = sorted(set(state.get(src, [])) | set(rows))
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    print(f"Nových položek: {sum(len(r) for r in new.values())}")


if __name__ == "__main__":
    main()
