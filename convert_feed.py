#!/usr/bin/env python3
"""
Stahne skladovy feed z mijeurope.com a prevede ho na CSV
kompatibilni se Shoptet automatickym importem skladovych zasob.

Vystup: dva soubory
  - stock_ean.csv  -> pro produkty, ktere maji EAN (parovani v Shoptetu podle EAN)
  - stock_kod.csv  -> pro 22 produktu bez EAN (parovani podle kodu produktu 'code')
                       POZOR: over, jestli tyto kody odpovidaji kodum produktu v Shoptetu.
"""

import csv
import os
import sys
import urllib.request

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

    rows_ean = []
    rows_kod = []
    skipped = 0

    for code, pair_code, name, ean, stock, _f in ws.iter_rows(min_row=2, values_only=True):
        if code is None:
            continue
        try:
            stock_int = max(0, int(str(stock).strip()))
        except (TypeError, ValueError):
            skipped += 1
            continue

        if ean:
            rows_ean.append((str(ean).strip(), stock_int))
        else:
            rows_kod.append((str(code).strip(), stock_int))

    ean_path = os.path.join(OUT_DIR, "stock_ean.csv")
    with open(ean_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ean", "pocet"])
        w.writerows(rows_ean)

    kod_path = os.path.join(OUT_DIR, "stock_kod.csv")
    with open(kod_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["kod", "pocet"])
        w.writerows(rows_kod)

    os.remove(tmp_xlsx)

    print(f"Hotovo: {len(rows_ean)} radku podle EAN, {len(rows_kod)} radku podle kodu, {skipped} preskoceno.")


if __name__ == "__main__":
    main()
