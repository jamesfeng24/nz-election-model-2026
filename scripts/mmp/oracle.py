"""Build the official seat-table oracle for the MMP allocator from preserved raw CSVs.

Run: python3 -m scripts.mmp.oracle          (write data/processed/mmp/oracle-seat-tables.json)
     python3 -m scripts.mmp.oracle --check  (verify the committed file regenerates byte-for-byte)

Inputs are the Electoral Commission "Summary of Overall Results" tables for 2008-2023.
Party-vote totals and official seats are copied, never imputed; nothing is fitted.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/processed/mmp/oracle-seat-tables.json"
SOURCES = {
    2008: "data/raw/elections/2008/e9/csv/e9_part1.csv",
    2011: "data/raw/elections/2011/e9/csv/e9_part1.csv",
    2014: "data/raw/elections/2014/e9/csv/e9_part1.csv",
    2017: "data/raw/elections/2017/statistics/csv/overall-results-summary.csv",
    2020: "data/raw/elections/2020/statistics/csv/overall-results-summary.csv",
    2023: "data/raw/elections/2023/statistics/csv/overall-results-summary.csv",
}


def _int(cell: str):
    cell = cell.strip()
    return int(cell) if cell else None


def parse_summary(raw: bytes) -> dict:
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
    section = None
    listed, unlisted, unregistered = [], [], []
    for row in rows:
        name = row[0].strip() if row else ""
        if name == "Registered Parties with List":
            section = "registered"
            continue
        if name == "Unregistered Parties":
            section = "unregistered"
            continue
        if section is None or len(row) < 6 or not name:
            continue
        list_seats, list_votes, seats_won = _int(row[1]), _int(row[2]), _int(row[5])
        if section == "unregistered":
            unregistered.append({"partyName": name, "constituencySeats": seats_won or 0})
        elif list_votes is None:
            unlisted.append({"partyName": name, "constituencySeats": seats_won or 0})
        else:
            listed.append({"partyName": name, "partyVotes": list_votes,
                           "officialListSeats": list_seats or 0,
                           "constituencySeats": seats_won or 0})
    return {
        "listedParties": listed,
        "constituencySeatsOutsidePartyBallot": sum(
            r["constituencySeats"] for r in unlisted + unregistered),
    }


def build() -> dict:
    elections = []
    for year, rel in SOURCES.items():
        raw = (ROOT / rel).read_bytes()
        parsed = parse_summary(raw)
        record = {"year": year, "rawPath": rel,
                  "rawSha256": hashlib.sha256(raw).hexdigest(), **parsed}
        record["officialParliamentSize"] = sum(
            p["officialListSeats"] + p["constituencySeats"] for p in parsed["listedParties"]
        ) + parsed["constituencySeatsOutsidePartyBallot"]
        elections.append(record)
    return {
        "schemaVersion": 1,
        "description": "Official party-vote totals, constituency seats and list seats from the "
                       "Electoral Commission summary of overall results, used only as allocator test oracles.",
        "limitations": [
            "officialListSeats are the Commission's 'Seats Allocated' column; 2023 excludes the "
            "postponed Port Waikato electorate poll, so its parliament size is the declaration-day 122.",
            "Component-party constituency wins are not separated in the source; none is assumed.",
        ],
        "elections": elections,
    }


def render(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    text = render(build())
    if "--check" in argv:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != text:
            print("oracle-seat-tables.json is missing or does not regenerate", file=sys.stderr)
            return 1
        print("oracle-seat-tables.json regenerates byte-for-byte")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
