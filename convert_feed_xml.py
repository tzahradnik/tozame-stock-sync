#!/usr/bin/env python3
"""
Stahne skladovy feed z mijeurope.com a prevede ho na XML ve formatu
Shoptet "dodavatelsky import" (products-supplier-v10.rng), ktery jde
nahrat rucne pres Produkty -> Import (bez placeneho Automatickeho importu).

Parovani: CODE (vzdy), + EAN kdyz je k dispozici.
Sklad: <STOCK><AMOUNT>N</AMOUNT></STOCK> - jednoducha hodnota bez skladu/lokace,
zaporne hodnoty se orizavaji na 0.
"""

import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from xml.dom import minidom

import openpyxl

FEED_URL = os.environ.get(
    "MIJEUROPE_FEED_URL",
    "https://www.mijeurope.com/export/products.xls?patternId=39&partnerId=4&hash=6f49d5c9010f126e77eede0fe909e2aad3e3074eddbd987b6ad7952b9418e1de",
)
OUT_DIR = os.environ.get("OUT_DIR", ".")


def download(url: str, dest: str) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "tozame-stock-sync/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as f:
        f.write(resp.read())


def main() -> None:
    tmp_xlsx = os.path.join(OUT_DIR, "_mijeurope_raw.xlsx")
    download(FEED_URL, tmp_xlsx)

    wb = openpyxl.load_workbook(tmp_xlsx, data_only=True)
    ws = wb["Products export"]

    shop = ET.Element("SHOP")
    count = 0
    skipped = 0

    for code, pair_code, name, ean, stock, _f in ws.iter_rows(min_row=2, values_only=True):
        if not code:
            skipped += 1
            continue
        try:
            stock_int = max(0, int(str(stock).strip()))
        except (TypeError, ValueError):
            skipped += 1
            continue

        item = ET.SubElement(shop, "SHOPITEM")
        ET.SubElement(item, "CODE").text = str(code).strip()
        if ean:
            ET.SubElement(item, "EAN").text = str(ean).strip()
        stock_el = ET.SubElement(item, "STOCK")
        ET.SubElement(stock_el, "AMOUNT").text = str(stock_int)
        count += 1

    xml_bytes = ET.tostring(shop, encoding="utf-8")
    pretty = minidom.parseString(xml_bytes).toprettyxml(indent="  ", encoding="utf-8")

    out_path = os.path.join(OUT_DIR, "stock_import.xml")
    with open(out_path, "wb") as f:
        f.write(pretty)

    os.remove(tmp_xlsx)
    print(f"Hotovo: {count} polozek zapsano do {out_path}, {skipped} preskoceno (chybi kod/neplatny sklad).")


if __name__ == "__main__":
    main()
