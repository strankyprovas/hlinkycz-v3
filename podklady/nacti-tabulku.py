#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Převede vyplněnou tabulku od Noviry na data pro web.

Použití:
    python3 podklady/nacti-tabulku.py podklady/jednotky-tabulka.csv

Přepíše byty/data/jednotky.json, ze kterého se plní přehled jednotek.
Řádky bez vyplněné dispozice přeskakuje — ještě nejsou hotové.
"""
import csv
import json
import os
import sys

ZDE = os.path.dirname(os.path.abspath(__file__))
VYSTUP = os.path.join(ZDE, "..", "byty", "data", "jednotky.json")

STAVY = {"volný", "rezervovaný", "obsazený"}


def karta_pro(dispozice):
    """Dokud nejsou karty jednotlivých bytů, míříme na vzorové."""
    if dispozice.startswith("obchodní"):
        return "obchodni-1a.html"
    return "1kk-vzor.html" if dispozice == "1+kk" else "2kk-vzor.html"


def cislo(hodnota, desetinne=False):
    hodnota = (hodnota or "").strip().replace(" ", "").replace("\xa0", "").replace(",", ".")
    if not hodnota:
        return None
    try:
        return float(hodnota) if desetinne else int(float(hodnota))
    except ValueError:
        return None


def main(cesta):
    with open(cesta, encoding="utf-8-sig") as f:
        radky = list(csv.DictReader(f, delimiter=";"))

    jednotky, preskoceno, problemy = [], 0, []

    for i, r in enumerate(radky, start=2):
        dispozice = (r.get("dispozice") or "").strip()
        if not dispozice:
            preskoceno += 1
            continue

        stav = (r.get("stav") or "").strip().lower()
        if stav and stav not in STAVY:
            problemy.append(f"řádek {i}: neznámý stav „{stav}\" (povoleno: volný / rezervovaný / obsazený)")
            stav = ""

        jednotky.append({
            "dum": (r.get("dum") or "").strip(),
            "patro": cislo(r.get("patro")) or 0,
            "oznaceni": (r.get("oznaceni") or "").strip(),
            "dispozice": dispozice,
            "plocha": cislo(r.get("plocha_m2"), desetinne=True) or 0,
            "cena": cislo(r.get("cena_kc_mesic")),
            "stav": stav or "volný",
            "nastehovani": (r.get("nastehovani") or "").strip(),
            "vystehovani": (r.get("vystehovani") or "").strip(),
            "pdf": (r.get("pdf_odkaz") or "").strip(),
            "poznamka": (r.get("poznamka") or "").strip(),
            "karta": karta_pro(dispozice),
        })

    import datetime
    data = {
        "aktualizovano": datetime.date.today().isoformat(),
        "zdroj": os.path.basename(cesta),
        "jednotky": jednotky,
    }
    with open(VYSTUP, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    print(f"načteno {len(jednotky)} jednotek, přeskočeno {preskoceno} nevyplněných")
    for p in problemy:
        print("  ⚠", p)
    print(f"zapsáno do {os.path.normpath(VYSTUP)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ZDE, "jednotky-tabulka.csv"))
