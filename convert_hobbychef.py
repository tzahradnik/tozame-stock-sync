"""Skladový feed HobbyChef (Yaxell, Hasegawa, Naniwa) -> Shoptet stock XML.

Feed: HOBBYCHEF_STOCK_URL (secret), formát <item_list><item id=".."><sku>..</sku><stock_quantity>..</stock_quantity>.
Kód produktu v Shoptetu = sku z feedu. Výstup: $OUT_DIR/stock_import_hobbychef.xml ve stejném formátu
jako stock_import.xml (SHOPITEM/CODE, STOCK/AMOUNT).
Při 429 (rate limit) počká a zkusí znovu, nejvýš 4 pokusy.
"""
import os
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

URL = os.environ["HOBBYCHEF_STOCK_URL"]
OUT_DIR = os.environ.get("OUT_DIR", "public")


def fetch(url):
    delay = 30
    for attempt in range(4):
        req = urllib.request.Request(url, headers={"User-Agent": "tozame-stock-sync/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 3:
                raise
            wait = int(e.headers.get("Retry-After") or delay)
            print(f"429, čekám {wait} s", file=sys.stderr)
            time.sleep(wait)
            delay *= 2


def main():
    body = fetch(URL)
    root = ET.fromstring(body)
    parts = ['<?xml version="1.0" encoding="utf-8"?>', "<SHOP>"]
    n = 0
    for item in root.findall("item"):
        sku = (item.findtext("sku") or "").strip()
        qty = item.findtext("stock_quantity")
        if not sku or qty is None:
            continue
        stock = max(0, int(float(qty)))
        parts.append("  <SHOPITEM>")
        parts.append(f"    <CODE>{escape(sku)}</CODE>")
        parts.append(f"    <STOCK>\n      <AMOUNT>{stock}</AMOUNT>\n    </STOCK>")
        parts.append("  </SHOPITEM>")
        n += 1
    parts.append("</SHOP>")
    if n == 0:
        sys.exit("Feed HobbyChef je prázdný, nic nezapisuji.")
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "stock_import_hobbychef.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(parts) + "\n")
    print(f"HobbyChef: {n} položek")


if __name__ == "__main__":
    main()
