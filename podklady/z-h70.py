#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Přidá jednotky z Hlinek 70 do jednotky-tabulka.csv.

Zdroj: „Jednotky H70.xlsx" (Lucie Krátká, 11. 8. 2026) — doplněné výměry
balkonů z prohlášení vlastníka.

Andrea (11. 8.): „Použij prosím jen žluté sloupečky." Žlutě jsou v hlavičce
označené tři: Ozn. vlastní (B), Podl. plocha (G) a Balkon / terasa (H).
Beru tedy jejich vlastní číslování, ne katastrální označení z KN.
Zbylé sloupce (typ, stav, podlaží, dispozice) jsou popisné a používám je
tak, jak jsou.

Ceny ani termíny nastěhování v souboru nejsou — zůstávají prázdné.

Použití:
    python3 podklady/z-h70.py ~/Downloads/"Jednotky H70.xlsx"
"""
import csv
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
ZDE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(ZDE, "jednotky-tabulka.csv")

STAVY = {"volný": "volný", "obsazený": "obsazený", "rezervovaný": "rezervovaný"}


def nacti_list(cesta):
    z = zipfile.ZipFile(cesta)
    sst = []
    if "xl/sharedStrings.xml" in z.namelist():
        r = ET.fromstring(z.read("xl/sharedStrings.xml"))
        sst = ["".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t"))
               for si in r.findall("m:si", NS)]
    sh = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    radky = []
    for row in sh.iter(f"{{{NS['m']}}}row"):
        b = {}
        for c in row.findall("m:c", NS):
            col = re.sub(r"\d", "", c.get("r"))
            v = c.find("m:v", NS)
            if v is not None:
                b[col] = sst[int(v.text)] if c.get("t") == "s" else v.text
        if b:
            radky.append(b)
    return radky[1:]          # bez hlavičky


def cislo(s, desetin=1):
    if not s:
        return ""
    return f"{float(s):.{desetin}f}".replace(".", ",")


def patro(s):
    m = re.match(r"(\d+)", s or "")
    return m.group(1) if m else ""


def main(cesta):
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    hlavicky = list(rows[0].keys())
    rows = [r for r in rows if r["dum"] != "Hlinky 70"]     # idempotentní

    nove = []
    for x in nacti_list(cesta):
        dispozice = (x.get("F") or "").strip()
        if dispozice == "obchodní jednotka":
            dispozice = "obchodní prostor"
        balkon = x.get("H") or "0"
        pozn = ""
        try:
            if float(balkon) > 0:
                pozn = f"balkon/terasa {cislo(balkon)} m²"
        except ValueError:
            pass
        nove.append({
            "dum": "Hlinky 70",
            "oznaceni": (x.get("B") or "").strip(),        # žlutý sloupec
            "patro": patro(x.get("E")),
            "dispozice": dispozice,
            "plocha_m2": cislo(x.get("G")),                # žlutý sloupec
            "cena_kc_mesic": "",                           # v souboru není
            "stav": STAVY.get((x.get("D") or "").strip().lower(), ""),
            "nastehovani": "",
            "vystehovani": "",
            "pdf_odkaz": "",
            "poznamka": pozn,                              # žlutý sloupec
        })

    rows.extend(nove)
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=hlavicky, delimiter=";")
        w.writeheader()
        w.writerows(rows)

    byty = [j for j in nove if j["dispozice"] != "obchodní prostor"]
    print(f"Hlinky 70: přidáno {len(nove)} jednotek "
          f"({len(byty)} bytů, {len(nove) - len(byty)} obchodní prostory)")
    print(f"tabulka má nyní {len(rows)} řádků")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1
         else os.path.expanduser("~/Downloads/Jednotky H70.xlsx"))
