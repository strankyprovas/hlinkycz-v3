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


def karta_pro(dispozice, oznaceni="", dum=""):
    """Dokud nejsou karty jednotlivých bytů, míříme na vzorové.

    Hlinky 70 zatím žádné karty nemají a vzorové karty z novostaveb by tam
    byly zavádějící — u nich radši žádný odkaz."""
    if dum == "Hlinky 70":
        return ""
    if dispozice.startswith("obchodní"):
        # obchodní prostory mají vlastní karty 1A / 1B / 1C
        return f"obchodni-{oznaceni.lower()}.html" if oznaceni else "obchodni-1a.html"
    if dispozice == "1+kk":
        return "1kk-vzor.html"
    if dispozice == "2+kk":
        return "2kk-vzor.html"
    return ""   # 1+1 a 2+1 vzorovou kartu nemají


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
        # byty vč. energií a DPH, komerce nájem bez DPH — dle zadání Noviry
        rezim = "komerce" if dispozice.startswith("obchodní") else "byt"

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
            "stav": stav,   # prázdné = dostupnost zatím nedoplněná, nevydávat za volné
            "nastehovani": (r.get("nastehovani") or "").strip(),
            "vystehovani": (r.get("vystehovani") or "").strip(),
            "pdf": (r.get("pdf_odkaz") or "").strip(),
            "poznamka": (r.get("poznamka") or "").strip(),
            "karta": karta_pro(dispozice, (r.get("oznaceni") or "").strip(),
                               (r.get("dum") or "").strip()),
            "cenovy_rezim": rezim,
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
