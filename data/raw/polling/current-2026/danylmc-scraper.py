#!/usr/bin/env python3
"""
NZ Election Polling Data Scraper
Scrapes opinion polling data from Wikipedia for NZ elections 1993-2026
"""

import argparse
import json
import re
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup
import pandas as pd


# Election years to scrape (NZ elections roughly every 3 years)
ELECTION_YEARS = [1993, 1996, 1999, 2002, 2005, 2008, 2011, 2014, 2017, 2020, 2023, 2026]

# Wikipedia URL pattern
URL_TEMPLATE = "https://en.wikipedia.org/wiki/Opinion_polling_for_the_{year}_New_Zealand_general_election"

# Headers to avoid 403 blocks
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# Party name normalization mapping
PARTY_ALIASES = {
    # National
    "nat": "National",
    "national": "National",
    "nats": "National",
    # Labour
    "lab": "Labour",
    "labour": "Labour",
    # Green
    "grn": "Green",
    "green": "Green",
    "greens": "Green",
    "green party": "Green",
    # ACT
    "act": "ACT",
    "act nz": "ACT",
    "act new zealand": "ACT",
    # NZ First
    "nzf": "NZ First",
    "nz first": "NZ First",
    "new zealand first": "NZ First",
    "nzfirst": "NZ First",
    # Te Pati Maori
    "tpm": "Te Pāti Māori",
    "māori": "Te Pāti Māori",
    "maori": "Te Pāti Māori",
    "te pāti māori": "Te Pāti Māori",
    "te pati maori": "Te Pāti Māori",
    "maori party": "Te Pāti Māori",
    # TOP
    "top": "TOP",
    "opportunities": "TOP",
    "the opportunities party": "TOP",
    "opp": "TOP",
    "opportunity": "TOP",
    "opportunity party": "TOP",
    # United Future
    "uf": "United Future",
    "united": "United Future",
    "united future": "United Future",
    # Alliance
    "alliance": "Alliance",
    # Progressive
    "prog": "Progressive",
    "progressive": "Progressive",
    # Mana
    "mana": "Mana",
    # Internet-Mana
    "internet-mana": "Internet-Mana",
    # Conservative
    "con": "Conservative",
    "conservative": "Conservative",
    # New Conservative
    "ncp": "New Conservative",
    "new conservative": "New Conservative",
}

# Known party columns to look for (case-insensitive)
KNOWN_PARTIES = [
    "national", "labour", "green", "act", "nz first", "new zealand first",
    "māori", "maori", "te pāti māori", "top", "opp", "opportunity",
    "united future", "united",
    "alliance", "progressive", "mana", "conservative", "new conservative",
    "nzf", "grn", "tpm", "nat", "lab", "mri"  # MRI = Maori abbreviated
]

# Add abbreviated forms for header matching
PARTY_ALIASES["mri"] = "Te Pāti Māori"


def clean_text(text: str) -> str:
    """Remove footnotes, references, and clean whitespace"""
    if not text:
        return ""
    # Remove footnote references like [1], [a], [note 1]
    text = re.sub(r'\[[\w\s]+\]', '', text)
    # Remove superscript references
    text = re.sub(r'[†‡§¶*]+', '', text)
    # Clean whitespace
    text = ' '.join(text.split())
    return text.strip()


def normalize_party_name(name: str) -> Optional[str]:
    """Normalize party name to standard form"""
    if not name:
        return None
    cleaned = clean_text(name).lower().strip()
    return PARTY_ALIASES.get(cleaned, name.strip())


def normalize_pollster_name(name: str) -> Optional[str]:
    """Normalize a pollster name so the same firm reads identically everywhere.

    Wikipedia writes joined names ("Taxpayers’ Union–Curia", "1 News–Verian")
    inconsistently: the separator turns up as an en dash, an em dash or a
    spaced hyphen, and apostrophes come both straight and curly. Left alone
    that splits one pollster into several, which quietly breaks any grouping
    by firm — house-effect estimates most of all.
    """
    if not name:
        return None
    cleaned = clean_text(name)
    # Citation text from an archive link sometimes lands inside the cell.
    cleaned = re.sub(r"\s*Archived\s+.*?\s+at the Wayback Machine\s*$", "", cleaned,
                     flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*[—–-]\s*", "–", cleaned)
    cleaned = cleaned.replace("’", "'")
    return cleaned or None


def parse_percentage(value: str) -> Optional[float]:
    """Parse percentage value from string"""
    if not value:
        return None
    cleaned = clean_text(value)
    # Remove % sign and any other non-numeric chars except decimal point
    cleaned = re.sub(r'[^\d.]', '', cleaned)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_date(date_str: str, election_year: int) -> Optional[str]:
    """Parse date string to ISO format"""
    if not date_str:
        return None

    cleaned = clean_text(date_str)
    if not cleaned:
        return None

    # Common date patterns in Wikipedia polling tables
    patterns = [
        # "1-3 Oct 2023" or "1–3 Oct 2023"
        (r'(\d{1,2})[-–](\d{1,2})\s+(\w+)\s+(\d{4})', lambda m: f"{m.group(4)}-{month_to_num(m.group(3)):02d}-{int(m.group(2)):02d}"),
        # "1 Oct 2023"
        (r'(\d{1,2})\s+(\w+)\s+(\d{4})', lambda m: f"{m.group(3)}-{month_to_num(m.group(2)):02d}-{int(m.group(1)):02d}"),
        # "Oct 2023"
        (r'(\w+)\s+(\d{4})', lambda m: f"{m.group(2)}-{month_to_num(m.group(1)):02d}-01"),
        # "1-3 Oct" (no year, use election year)
        (r'(\d{1,2})[-–](\d{1,2})\s+(\w+)$', lambda m: f"{election_year}-{month_to_num(m.group(3)):02d}-{int(m.group(2)):02d}"),
        # "1 Oct" (no year)
        (r'(\d{1,2})\s+(\w+)$', lambda m: f"{election_year}-{month_to_num(m.group(2)):02d}-{int(m.group(1)):02d}"),
        # "October 2023"
        (r'(\w+)\s+(\d{4})', lambda m: f"{m.group(2)}-{month_to_num(m.group(1)):02d}-01"),
    ]

    for pattern, formatter in patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            try:
                return formatter(match)
            except (ValueError, KeyError):
                continue

    return None


def parse_fieldwork_period(date_str: str, election_year: int) -> tuple[Optional[str], Optional[str]]:
    """Return the start and end dates represented by a polling-table date."""
    cleaned = clean_text(date_str)
    end_iso = parse_date(cleaned, election_year)
    if not end_iso:
        return None, None
    try:
        end = datetime.strptime(end_iso, "%Y-%m-%d")
    except ValueError:
        return None, None

    # Different months: "27 Jul – 23 Aug 2026".
    match = re.search(
        r'(\d{1,2})\s+(\w+)(?:\s+(\d{4}))?\s*[-–—]\s*'
        r'(\d{1,2})\s+(\w+)\s+(\d{4})',
        cleaned,
        re.IGNORECASE,
    )
    if match:
        # Wikipedia occasionally carries an impossible date ("31 Sep - 11 Oct
        # 2015"). Fall through to the single-date result rather than crashing
        # the whole scrape over one typo.
        try:
            start_year = int(match.group(3) or match.group(6))
            start_month = month_to_num(match.group(2))
            end_month = month_to_num(match.group(5))
            end = datetime(int(match.group(6)), end_month, int(match.group(4)))
            if not match.group(3) and start_month > end_month:
                start_year -= 1
            start = datetime(start_year, start_month, int(match.group(1)))
            return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
        except (ValueError, KeyError):
            return end_iso, end_iso

    # Same month: "14–21 Aug 2026".
    match = re.search(
        r'(\d{1,2})\s*[-–—]\s*(\d{1,2})\s+(\w+)\s+(\d{4})',
        cleaned,
        re.IGNORECASE,
    )
    if match:
        try:
            start = datetime(int(match.group(4)), month_to_num(match.group(3)), int(match.group(1)))
        except (ValueError, KeyError):
            return end_iso, end_iso
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    return end_iso, end_iso


def month_to_num(month_str: str) -> int:
    """Convert month name to number"""
    months = {
        'jan': 1, 'january': 1,
        'feb': 2, 'february': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8,
        'sep': 9, 'sept': 9, 'september': 9,
        'oct': 10, 'october': 10,
        'nov': 11, 'november': 11,
        'dec': 12, 'december': 12,
    }
    return months.get(month_str.lower()[:3], 1)


def identify_party_columns(headers: list) -> dict:
    """Identify which columns contain party data"""
    party_cols = {}
    for idx, header in enumerate(headers):
        header_lower = clean_text(header).lower()
        for party in KNOWN_PARTIES:
            if party in header_lower or header_lower in party:
                normalized = normalize_party_name(header)
                if normalized:
                    party_cols[idx] = normalized
                break
    return party_cols


def get_table_headers(table: BeautifulSoup) -> list:
    """Extract headers from a table, handling multi-row headers"""
    rows = table.find_all('tr')
    if not rows:
        return []

    headers = []
    # Check first two rows for headers (some tables have multi-row headers)
    for row_idx, row in enumerate(rows[:2]):
        cells = row.find_all(['th', 'td'])
        row_headers = []
        for cell in cells:
            colspan = int(cell.get('colspan', 1))
            text = clean_text(cell.get_text())
            row_headers.extend([text] * colspan)

        if row_idx == 0:
            headers = row_headers
        else:
            # Merge second row headers if they contain party names
            row_text = ' '.join(row_headers).lower()
            if any(party in row_text for party in ['national', 'labour', 'green', 'act', 'nat', 'lab']):
                # Use second row as headers
                headers = row_headers

    return headers


def score_table(table: BeautifulSoup) -> int:
    """Score a table based on how likely it is to be a polling table"""
    headers = get_table_headers(table)
    header_text = ' '.join(headers).lower()

    score = 0
    # Score based on party name presence (both full and abbreviated)
    party_matches = ['national', 'labour', 'green', 'act', 'nz first', 'nat', 'lab', 'grn', 'nzf', 'mri']
    for party in party_matches:
        # Exact word match to avoid false positives
        if re.search(r'\b' + party + r'\b', header_text):
            score += 10

    # Score based on poll-related column names
    poll_indicators = ['date', 'poll', 'sample', 'margin', 'firm', 'organisation', 'polling']
    for indicator in poll_indicators:
        if indicator in header_text:
            score += 5

    # Score based on number of data rows (prefer larger tables)
    rows = table.find_all('tr')
    score += min(len(rows) // 2, 30)  # Higher weight for row count

    return score


def find_polling_table(soup: BeautifulSoup) -> Optional[BeautifulSoup]:
    """Find the main polling table on the page"""
    # Collect ALL potential polling tables (both wikitable and sortable)
    tables = []
    wikitables = soup.find_all('table', class_='wikitable')
    sortable_tables = soup.find_all('table', class_='sortable')

    # Combine both lists, avoiding duplicates
    seen = set()
    for table in wikitables + sortable_tables:
        table_id = id(table)
        if table_id not in seen:
            seen.add(table_id)
            tables.append(table)

    if not tables:
        return None

    # Score all tables and pick the best one
    best_table = None
    best_score = 0

    for table in tables:
        score = score_table(table)
        if score > best_score:
            best_score = score
            best_table = table

    # Require a minimum score
    if best_score < 15:
        # Fall back to first table with National/Labour
        for table in tables:
            headers = get_table_headers(table)
            header_text = ' '.join(headers).lower()
            if 'national' in header_text or 'labour' in header_text or 'nat' in header_text or 'lab' in header_text:
                return table

    return best_table


def scrape_election_year(year: int, session: requests.Session) -> dict:
    """Scrape polling data for a single election year"""
    url = URL_TEMPLATE.format(year=year)
    print(f"  Fetching {url}")

    try:
        response = session.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Error fetching {year}: {e}")
        return {"election_year": year, "polls": [], "error": str(e)}

    soup = BeautifulSoup(response.content, 'lxml')

    # Find the polling table
    table = find_polling_table(soup)
    if not table:
        print(f"  No polling table found for {year}")
        return {"election_year": year, "polls": [], "error": "No table found"}

    # Parse headers
    rows = table.find_all('tr')
    if not rows:
        return {"election_year": year, "polls": [], "error": "No rows found"}

    # Get headers (handles multi-row headers)
    headers = get_table_headers(table)

    # Identify party columns and other columns
    party_cols = identify_party_columns(headers)

    # Determine which row to start data from (skip header rows)
    start_row = 1
    if len(rows) > 1:
        # Check if second row is also headers (contains party names)
        second_row_text = clean_text(rows[1].get_text()).lower()
        if any(party in second_row_text for party in ['national', 'labour', 'green']):
            start_row = 2

    # Find date/pollster columns
    date_col = None
    pollster_col = None
    sample_col = None

    for idx, header in enumerate(headers):
        header_lower = header.lower()
        if 'date' in header_lower or 'poll' in header_lower and date_col is None:
            if any(label in header_lower for label in
                   ('pollster', 'firm', 'company', 'organisation', 'organization')):
                pollster_col = idx
            else:
                date_col = idx
        elif any(label in header_lower for label in
                 ('pollster', 'firm', 'company', 'organisation', 'organization')):
            pollster_col = idx
        elif 'sample' in header_lower or 'size' in header_lower or 'n=' in header_lower:
            sample_col = idx

    # Parse data rows
    polls = []
    for row in rows[start_row:]:  # Skip header row(s)
        cells = row.find_all(['td', 'th'])
        if len(cells) < 3:  # Skip rows that are too short
            continue

        # Extract cell values
        cell_values = []
        for cell in cells:
            colspan = int(cell.get('colspan', 1))
            text = clean_text(cell.get_text())
            cell_values.extend([text] * colspan)

        # Skip if row is too short
        if len(cell_values) < max(party_cols.keys(), default=0) + 1:
            continue

        # Extract poll data
        poll_data = {
            "date": None,
            "fieldwork_start": None,
            "fieldwork_end": None,
            "pollster": None,
            "sample_size": None,
            "parties": {}
        }

        # Get date
        if date_col is not None and date_col < len(cell_values):
            start, end = parse_fieldwork_period(cell_values[date_col], year)
            poll_data["date"] = end
            poll_data["fieldwork_start"] = start
            poll_data["fieldwork_end"] = end
        elif date_col is None and len(cell_values) > 0:
            # Try first column as date fallback
            start, end = parse_fieldwork_period(cell_values[0], year)
            poll_data["date"] = end
            poll_data["fieldwork_start"] = start
            poll_data["fieldwork_end"] = end

        # Get pollster
        if pollster_col is not None and pollster_col < len(cell_values):
            poll_data["pollster"] = normalize_pollster_name(cell_values[pollster_col])

        # Get sample size
        if sample_col is not None and sample_col < len(cell_values):
            sample_str = cell_values[sample_col]
            sample_match = re.search(r'[\d,]+', sample_str.replace(',', ''))
            if sample_match:
                try:
                    poll_data["sample_size"] = int(sample_match.group().replace(',', ''))
                except ValueError:
                    pass

        # Get party percentages
        for col_idx, party_name in party_cols.items():
            if col_idx < len(cell_values):
                pct = parse_percentage(cell_values[col_idx])
                if pct is not None and 0 <= pct <= 100:
                    poll_data["parties"][party_name] = pct

        # Reject rows whose parsed party shares cannot represent a vote split.
        # This also guards against future table-layout changes shifting columns.
        party_total = sum(poll_data["parties"].values())
        if poll_data["parties"] and party_total <= 105:
            polls.append(poll_data)

    print(f"  Found {len(polls)} polls for {year}")
    return {
        "election_year": year,
        "source": url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "polls": polls,
    }


def main():
    """Main function to scrape all election years"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--year",
        type=int,
        choices=ELECTION_YEARS,
        help="scrape one election cycle instead of replacing every data file",
    )
    args = parser.parse_args()
    years = [args.year] if args.year else ELECTION_YEARS

    print("NZ Election Polling Data Scraper")
    print("=" * 40)

    output_dir = Path(__file__).parent / "data"
    output_dir.mkdir(exist_ok=True)

    session = requests.Session()

    for year in years:
        print(f"\nScraping {year} election polling data...")

        data = scrape_election_year(year, session)

        # Save to JSON
        output_file = output_dir / f"{year}_polling.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"  Saved to {output_file}")

        # Rate limiting - be respectful to Wikipedia
        time.sleep(1.5)

    print("\n" + "=" * 40)
    print("Scraping complete!")

    # Print summary
    total_polls = 0
    for year in years:
        output_file = output_dir / f"{year}_polling.json"
        if output_file.exists():
            with open(output_file, 'r') as f:
                data = json.load(f)
                total_polls += len(data.get("polls", []))

    print(f"Total polls collected: {total_polls}")


if __name__ == "__main__":
    main()
