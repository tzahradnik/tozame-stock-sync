#!/usr/bin/env python3
"""
Stahne skladovy feed z mijeurope.com a prevede ho na XML ve formatu
Shoptet "dodavatelsky import" (products-supplier-v10.rng), ktery jde
nahrat rucne pres Produkty -> Import (bez placeneho Automatickeho importu).

Bezpecnostni pojistka: posila se JEN polozka, kterou jde overit proti
shoptet_reference.json (export skutecnych kodu/EAN z Shoptetu) - bud
podle EAN, nebo podle kodu s odstranenym prefixem "MIJ". Polozky bez
overene shody (admin/logisticke radky jako Paleta, Dobirka, Box, nebo
produkty, ktere v Shoptetu proste jeste nejsou) se NEPOSILAJI, aby
import necekane nezalozil nove, prazdne produkty. Misto toho se zapisou
do unmatched_products.csv pro rucni kontrolu.

shoptet_reference.json se generuje jednorazove z exportu
Produkty -> Export v Shoptet administraci a je potreba ho obcas obnovit,
kdyz pribudou nove produkty.
"""

import csv
import json
import os
import urllib.request

import openpyxl

FEED_URL = os.environ.get(
    "MIJEUROPE_FEED_URL",
    "https://www.mijeurope.com/export/products.xls?patternId=39&partnerId=4&hash=6f49d5c9010f126e77eede0fe909e2aad3e3074eddbd987b6ad7952b9418e1de",
)
OUT_DIR = os.environ.get("OUT_DIR", ".")
REFERENCE_PATH = os.environ.get("REFERENCE_PATH", "shoptet_reference.json")


def download(url: str, dest: str) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "tozame-stock-sync/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as f:
        f.write(resp.read())


def strip_mij_prefix(code: str) -> str:
    return code[3:] if code.startswith("MIJ") else code


def main() -> None:
    with open(REFERENCE_PATH, encoding="utf-8") as f:
        reference = json.load(f)
    known_eans = set(reference["eans"])
    known_codes = set(reference["codes"])

    tmp_xlsx = os.path.join(OUT_DIR, "_mijeurope_raw.xlsx")
    download(FEED_URL, tmp_xlsx)

    wb = openpyxl.load_workbook(tmp_xlsx, data_only=True)
    ws = wb["Products export"]

    matched_lines = []
    unmatched_rows = []

    for code, pair_code, name, ean, stock, _f in ws.iter_rows(min_row=2, values_only=True):
        if not code:
            continue
        try:
            stock_int = max(0, int(str(stock).strip()))
        except (TypeError, ValueError):
            continue

        code = str(code).strip()
        ean = str(ean).strip() if ean else None
        stripped = strip_mij_prefix(code)

        ean_ok = ean is not None and ean in known_eans
        code_ok = stripped in known_codes

        if ean_ok or code_ok:
            matched_lines.append((stripped if code_ok else None, ean if ean_ok else None, stock_int))
        else:
            unmatched_rows.append((code, ean or "", name or "", stock_int))

    # --- XML jen s overenymi polozkami ---
    xml_parts = ['<?xml version="1.0" encoding="utf-8"?>', "<SHOP>"]
    for shoptet_code, ean, stock_int in matched_lines:
        xml_parts.append("  <SHOPITEM>")
        if shoptet_code:
            xml_parts.append(f"    <CODE>{shoptet_code}</CODE>")
        if ean:
            xml_parts.append(f"    <EAN>{ean}</EAN>")
        xml_parts.append(f"    <STOCK>\n      <AMOUNT>{stock_int}</AMOUNT>\n    </STOCK>")
        xml_parts.append("  </SHOPITEM>")
    xml_parts.append("</SHOP>")

    out_path = os.path.join(OUT_DIR, "stock_import.xml")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(xml_parts) + "\n")

    # --- report nenamapovanych radku k rucni kontrole ---
    unmatched_path = os.path.join(OUT_DIR, "unmatched_products.csv")
    with open(unmatched_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["mijeurope_code", "mijeurope_ean", "name", "stock"])
        w.writerows(unmatched_rows)

    os.remove(tmp_xlsx)
    print(
        f"Hotovo: {len(matched_lines)} položek odesláno do {out_path}, "
        f"{len(unmatched_rows)} vynecháno -> {unmatched_path}"
    )


if __name__ == "__main__":
    main()
