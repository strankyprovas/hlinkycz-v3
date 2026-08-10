#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vygeneruje jednotky-tabulka.csv z ceníkového XLS, který posílá Novira
(Hlinky_74_80_Cenik.xlsx, listy „HLINKY 74" a „HLINKY 80").

Bere jen byty a obchodní prostory — sklepy a parkovací místa vynechává.
Sloupce stav / nastěhování / vystěhování nechává prázdné, ty v ceníku
nejsou a musí je doplnit Novira.

Použití:
    python3 podklady/z-ceniku-noviry.py ~/Downloads/Hlinky_74_80_Cenik.xlsx
"""
import csv
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
ZDE = os.path.dirname(os.path.abspath(__file__))
VYSTUP = os.path.join(ZDE, "jednotky-tabulka.csv")

# každý list má sloupce jinde (74 má navíc „Označ. v PD")
LISTY = [
    # (sheet, dům, sloupec označení/typ/plocha/terasa/orientace/cena-web)
    ("xl/worksheets/sheet2.xml", "Hlinky 74", "B", "C", "E", "F", "G", "W"),
    ("xl/worksheets/sheet3.xml", "Hlinky 80", "B", "C", "D", "E", "F", "V"),
]


def nacti_sdilene(z):
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    return [
        "".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t"))
        for si in root.findall("m:si", NS)
    ]


def radky(z, sheet, sst):
    root = ET.fromstring(z.read(sheet))
    for row in root.iter(f"{{{NS['m']}}}row"):
        bunky = {}
        for c in row.findall("m:c", NS):
            v = c.find("m:v", NS)
            if v is None:
                continue
            hodnota = sst[int(v.text)] if c.get("t") == "s" else v.text
            bunky[re.sub(r"[0-9]", "", c.get("r"))] = hodnota
        if bunky:
            yield bunky


def dispozice(typ):
    """Z „Ubytovací j. 2+kk (invalidé)" udělá „2+kk"."""
    if "Komerční" in typ:
        return "obchodní prostor"
    m = re.search(r"([0-9]\+(?:kk|[0-9]))", typ)
    return m.group(1) if m else ""


def patro(podlazi):
    m = re.match(r"([0-9]+)\.NP", podlazi or "")
    return m.group(1) if m else ""


def poznamka(typ, terasa):
    casti = []
    if "invalid" in typ:
        casti.append("bezbariérová")
    if "velká terasa" in typ:
        casti.append("velká terasa")
    # „ubytovací jednotka" do poznámky nedávám — Novira chce všude psát „byty",
    # rozlišení se řeší až ve smlouvě (Andrea, 10. 8. 2026)
    try:
        if terasa and float(terasa.replace(",", ".")) > 0:
            m2 = f"{round(float(terasa.replace(',', '.')), 1):.1f}".replace(".", ",")
            casti.append(f"terasa {m2} m²")
    except ValueError:
        pass
    return ", ".join(casti)


# obchodní prostory ceník neoznačuje 1A/1B/1C a u Hlinek 74 je dělí na
# prodejnu a sklad — web je má jako jednu jednotku 1C. Ceny v ceníku nejsou,
# beru je z karet, které už na webu jsou.
OBCHODNI = {
    ("Hlinky 80", "1A"): ("1A", "53,5", "20330", ""),
    ("Hlinky 80", "1B"): ("1B", "206,8", "78584", "regulovatelná příčka"),
    ("Hlinky 74", "komerce"): ("1C", "71,7", "23371",
                               "31,1 m² prodejna + 34,1 m² zázemí/sklad"),
}


def slouc_obchodni_74(vystup):
    for j in vystup:
        klic = (j["dum"], j["oznaceni"])
        if klic in OBCHODNI:
            j["oznaceni"], j["plocha_m2"], j["cena_kc_mesic"], j["poznamka"] = OBCHODNI[klic]


def main(cesta):
    z = zipfile.ZipFile(cesta)
    sst = nacti_sdilene(z)
    vystup = []

    for sheet, dum, c_ozn, c_typ, c_plocha, c_terasa, c_orient, c_cena in LISTY:
        for r in radky(z, sheet, sst):
            typ = r.get(c_typ, "")
            ozn = r.get(c_ozn, "")
            if not typ or not ozn:
                continue
            if "Sklep" in typ or "Parkovací" in typ or "sklad" in typ:
                continue
            if not ("j." in typ or "jednotka" in typ):
                continue

            plocha = (r.get(c_plocha) or "").replace(".", ",")
            if plocha:
                plocha = f"{float(plocha.replace(',', '.')):.1f}".replace(".", ",")
            cena = r.get(c_cena) or ""
            if cena:
                cena = str(int(round(float(cena))))

            vystup.append({
                "dum": dum,
                "oznaceni": ozn,
                "patro": patro(r.get("A")),
                "dispozice": dispozice(typ),
                "plocha_m2": plocha,
                "cena_kc_mesic": cena,
                "stav": "",
                "nastehovani": "",
                "vystehovani": "",
                "pdf_odkaz": "",
                "poznamka": poznamka(typ, r.get(c_terasa)),
            })

    slouc_obchodni_74(vystup)

    with open(VYSTUP, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(vystup[0].keys()), delimiter=";")
        w.writeheader()
        w.writerows(vystup)

    byty = [j for j in vystup if j["dispozice"] != "obchodní prostor"]
    print(f"zapsáno {len(vystup)} jednotek do {os.path.basename(VYSTUP)}")
    print(f"  z toho bytů: {len(byty)}, obchodních prostor: {len(vystup) - len(byty)}")
    for dum in ("Hlinky 74", "Hlinky 80"):
        print(f"  {dum}: {sum(1 for j in vystup if j['dum'] == dum)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
        "~/Downloads/Hlinky_74_80_Cenik.xlsx"))
