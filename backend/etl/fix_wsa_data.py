"""
etl/fix_wsa_data.py
-------------------
One-time data fix script. Run AFTER the ETL and WHILE the backend is stopped.

Steps:
  1. Delete dummy seed rows (name like "% WSA ##")
  2. Delete known garbage rows (parser false-positives)
  3. Apply static province corrections
  4. Remove near-duplicates (keep the row with more data)
  5. Geocode every WSA with lat=0 / lng=0 using Nominatim (OpenStreetMap)

Usage:
    PYTHONPATH=. .venv/bin/python etl/fix_wsa_data.py
"""

import re
import time

import httpx
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import WSA

# --- known false-positives the parser extracted from non-data table rows ---
GARBAGE_NAMES = {
    "BDRR 2022", "BDRR 2023", "Capacity Utilisation", "Performance Trend",
    "Risk Category Split", "BD PAT", "BD Audit", "WSA Name", "WSPs",
    # partial / malformed names from split PDF cells
    "Magalies Water - Cullinan,", "Magalies Water - Vaalkop",
    "Rand Water-Vereeniging &",
    # water treatment works — not a WSA
    "Midmar WTP",
    # duplicate water board entries with footnote markers
    "Bloem Water now Vaal Central",  # keep "Bloem Water now Vaal Central Water"
    "Mangaung",                       # keep "Mangaung MM"
}

# --- static province corrections for municipalities misclassified by the parser ---
PROVINCE_CORRECTIONS = {
    # Gauteng metros/locals (came from GD25 Gauteng report)
    "City of Ekurhuleni": "Gauteng",
    "City of Johannesburg": "Gauteng",
    "City of Tshwane": "Gauteng",
    "Emfuleni LM": "Gauteng",
    "Lesedi LM": "Gauteng",
    "Merafong City LM": "Gauteng",
    "Merafong LM": "Gauteng",
    "Mogale City LM": "Gauteng",
    "Rand West City LM": "Gauteng",
    "Rand West LM": "Gauteng",
    "Midvaal LM": "Gauteng",
    # Limpopo water board / district misclassified as Gauteng
    "Greater Sekhukhune DM": "Limpopo",
    "Lepelle Northern Water": "Limpopo",
    # Northern Cape municipalities misclassified as Western Cape
    "Joe Morolong LM": "Northern Cape",
    "Kamiesberg LM": "Northern Cape",
    "Khai-Ma LM": "Northern Cape",
    "Richtersveld LM": "Northern Cape",
    "Ga-Segonyana LM": "Northern Cape",
    # North West municipality misclassified as Western Cape
    "Ngaka Modiri Molema DM": "North West",
    "Dr. Ruth S Mompati DM": "North West",
}

# --- near-duplicates: keep the canonical name, delete the alias ---
DUPLICATES_TO_REMOVE = {
    "Merafong LM",          # canonical is "Merafong City LM"
    "Rand West LM",         # canonical is "Rand West City LM"
    # Blue Drop PDF marks water board service areas with * and ** — duplicates of the base name
    "Govan Mbeki LM**", "Maquassi Hills LM**", "Matlosana LM**",
    "Mogalakwena LM**", "Moretele LM**",
    "Msunduzi LM*", "Msunduzi LM**",
    "Nala LM*",
    # Modimolle/Mookgophong appears twice with different slash formats
    "Modimolle/ Mookgophong LM",  # canonical is "Modimolle/Mookgophong LM"
}

# --- Nominatim search aliases for names that don't geocode well as-is ---
GEOCODE_ALIASES = {
    "Dr Beyers Naude LM": "Beaufort West Municipality, Western Cape, South Africa",
    "Dr. Ruth S Mompati DM": "Ruth Segomotsi Mompati District, North West, South Africa",
    "!Kai! Garib LM": "!Kai !Garib Local Municipality, Northern Cape, South Africa",
    "!Kheis LM": "!Kheis Local Municipality, Northern Cape, South Africa",
    "iLembe DM": "iLembe District Municipality, KwaZulu-Natal, South Africa",
    "Mbombela/Umjindi": "Mbombela, Mpumalanga, South Africa",
    "Maluti-a-Phofung LM": "Maluti-a-Phofung, Free State, South Africa",
    "Amatola Water": "King William's Town, Eastern Cape, South Africa",
    "Lepelle Northern Water": "Polokwane, Limpopo, South Africa",
    "Koukamma LM": "Koukamma Local Municipality, Eastern Cape, South Africa",
    "Albert Luthuli LM": "Chief Albert Luthuli Local Municipality, Mpumalanga, South Africa",
    "Umzinyathi DM": "Umzinyathi District Municipality, KwaZulu-Natal, South Africa",
    "Zululand DM": "Zululand District Municipality, KwaZulu-Natal, South Africa",
    "Nama Khoi LM": "Nama Khoi Local Municipality, Northern Cape, South Africa",
    "Ga-Segonyana LM": "Ga-Segonyana Local Municipality, Northern Cape, South Africa",
    "Kamiesberg LM": "Kamiesberg Local Municipality, Northern Cape, South Africa",
    "Khai-Ma LM": "Khai-Ma Local Municipality, Northern Cape, South Africa",
    "Joe Morolong LM": "Joe Morolong Local Municipality, Northern Cape, South Africa",
    "Ngaka Modiri Molema DM": "Ngaka Modiri Molema District Municipality, North West, South Africa",
    "OR Tambo DM": "O.R. Tambo District Municipality, Eastern Cape, South Africa",
    "Overberg Water": "Caledon, Western Cape, South Africa",
    "Mhlathuze Water": "Richards Bay, KwaZulu-Natal, South Africa",
    "Umgeni Water": "Pietermaritzburg, KwaZulu-Natal, South Africa",
    "Midvaal Water": "Meyerton, Gauteng, South Africa",
    "Bloem Water now Vaal Central Water": "Bloemfontein, Free State, South Africa",
    "Mangaung MM": "Bloemfontein, Free State, South Africa",
    "Modimolle/Mookgophong LM": "Modimolle, Limpopo, South Africa",
}

_DUMMY_PATTERN = re.compile(r"^(Eastern Cape|Free State|Gauteng|KwaZulu-Natal|Limpopo|Mpumalanga|Northern Cape|North West|Western Cape) WSA \d+$")


def geocode(name: str, province: str) -> tuple[float, float] | None:
    """Query Nominatim for a South African municipality. Returns (lat, lng) or None."""
    alias = GEOCODE_ALIASES.get(name)
    if alias:
        query = alias
    else:
        # try full name first, then stripped name
        cleaned = re.sub(r"\s+(LM|DM|MM|Metropolitan Municipality|Local Municipality|District Municipality)$", "", name, flags=re.IGNORECASE).strip()
        query = f"{cleaned}, {province}, South Africa"

    headers = {"User-Agent": "HydroSentinel/1.0 (student project)"}
    try:
        resp = httpx.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1, "countrycodes": "za"},
            headers=headers,
            timeout=10,
        )
        results = resp.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as exc:
        print(f"  geocode error for '{name}': {exc}")
    return None


def main() -> None:
    db: Session = SessionLocal()
    try:
        # 1. delete dummy seed rows
        dummy_count = 0
        for wsa in db.query(WSA).all():
            if _DUMMY_PATTERN.match(wsa.name):
                db.delete(wsa)
                dummy_count += 1
        db.commit()
        print(f"Deleted {dummy_count} dummy seed rows")

        # 2. delete garbage parser false-positives
        garbage_count = 0
        for wsa in db.query(WSA).all():
            if wsa.name in GARBAGE_NAMES or len(wsa.name.strip()) < 4:
                db.delete(wsa)
                garbage_count += 1
        db.commit()
        print(f"Deleted {garbage_count} garbage rows")

        # 3. delete near-duplicates
        dup_count = 0
        for wsa in db.query(WSA).all():
            if wsa.name in DUPLICATES_TO_REMOVE:
                db.delete(wsa)
                dup_count += 1
        db.commit()
        print(f"Deleted {dup_count} duplicate rows")

        # 4. apply province corrections
        fix_count = 0
        for wsa in db.query(WSA).all():
            correct_province = PROVINCE_CORRECTIONS.get(wsa.name)
            if correct_province and wsa.province != correct_province:
                wsa.province = correct_province
                fix_count += 1
        db.commit()
        print(f"Fixed {fix_count} province mismatches")

        # 5. geocode WSAs with missing coordinates
        wsas_to_geocode = db.query(WSA).filter(WSA.lat == 0.0, WSA.lng == 0.0).all()
        print(f"\nGeocoding {len(wsas_to_geocode)} WSAs (1 request/sec)...")

        success = 0
        failed = []
        for wsa in wsas_to_geocode:
            result = geocode(wsa.name, wsa.province)
            if result:
                wsa.lat, wsa.lng = result
                success += 1
                print(f"  ✓ {wsa.name:<45} → {wsa.lat:.4f}, {wsa.lng:.4f}")
            else:
                failed.append(wsa.name)
                print(f"  ✗ {wsa.name}")
            time.sleep(1.1)  # Nominatim rate limit: 1 req/sec

        db.commit()
        print(f"\nGeocoded {success}/{len(wsas_to_geocode)} WSAs successfully")

        # 6. manual fallback coordinates for WSAs Nominatim couldn't resolve
        manual_coords = {
            "Albert Luthuli LM":               (-26.7351, 30.4875),
            "Koukamma LM":                     (-33.9167, 23.9333),
            "Modimolle/Mookgophong LM":        (-24.7000, 28.4000),
            "OR Tambo DM":                     (-31.5000, 29.5000),
            "Overberg Water":                  (-34.2500, 19.4500),
            "Mhlathuze Water":                 (-28.7887, 31.9658),
            "Midvaal Water":                   (-26.6295, 28.0894),
            "Umgeni Water":                    (-29.6436, 30.3140),
            "Bloem Water now Vaal Central Water": (-29.1164, 26.2155),
            "Mangaung MM":                     (-29.1164, 26.2155),
        }
        manual_count = 0
        for wsa in db.query(WSA).filter(WSA.lat == 0.0, WSA.lng == 0.0).all():
            if wsa.name in manual_coords:
                wsa.lat, wsa.lng = manual_coords[wsa.name]
                manual_count += 1
                print(f"  manual ✓ {wsa.name}")
        db.commit()
        if manual_count:
            print(f"Applied {manual_count} manual coordinates")

        # final report
        total = db.query(WSA).count()
        no_coords = db.query(WSA).filter(WSA.lat == 0.0, WSA.lng == 0.0).count()
        print(f"\nFinal WSA count: {total}  |  Missing coords: {no_coords}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
