# NZ Election Polling Analysis

Statistical analysis of 30 years of New Zealand election polling data (1993-2026), deriving quantified "laws" of NZ politics.

## Key Findings

| # | Rule | Finding | Strength |
|---|------|---------|----------|
| 1 | **Incumbent Fatigue** | Governing parties lose ~1.6 points/year | Strong |
| 2 | **Punctuated Equilibrium** | Top 10% of weeks = 38% of total movement; 5x volatility ratio between "shift" and "stable" regimes | Strong |
| 3 | **Cross-Bloc Tides** | Left/right blocs move inversely (r = -0.706); average tide lasts 3.5 years | Strong |
| 4 | **Thermostatic Model** | Deviations self-correct at 0.15-0.18 pts per poll; asymmetric (faster from above) | Strong |
| 5 | **Economic Sentiment** | GDP growth, unemployment, and inflation all predict incumbent support at poll-level (n ~ 1,000) | Moderate |
| 6 | **Minor Party Volatility** | 3.2x more volatile (CV) than major parties; counter-cyclical with incumbent support | Moderate |
| 7 | **Leadership Honeymoon** | Mid-term bounces average +6.7 pts (Ardern +9, Hipkins +4.3) | Suggestive |
| 8 | **Crisis Rally** | Highly variable; COVID was +15 pts, others minimal | Suggestive |
| 9 | **Post-Election Reset** | Winners essentially flat (+0.1), losers drop slightly (-0.8) | Suggestive |
| 10 | **Election Convergence** | No clear convergence pattern detected | Suggestive |

Full analysis: [`reports/nz_rules.md`](reports/nz_rules.md)

## Data

- **1,016 party-vote polls** scraped from Wikipedia (1993-2026)
- **299 Preferred PM polls** (2008-2026)
- **Economic indicators** from World Bank API (GDP, unemployment, CPI; 1960-2024)
- **17 documented events** (leadership changes, crises, scandals)

## Project Structure

```
├── scraper.py             # Wikipedia party vote scraper
├── pm_scraper.py          # Preferred PM polling scraper
├── economic_scraper.py    # World Bank economic data scraper
├── events.py              # Political events timeline
├── analysis.py            # Initial statistical analysis (8 tests)
├── voter_flows.py         # Compositional data analysis (partial/log-return correlations)
├── nz_rules.py            # Laws of NZ Politics (10 analyses)
├── visualize.py           # Graph generation
├── data/
│   ├── *_polling.json     # Party vote polls by election year
│   ├── *_pm_polling.json  # PM preference polls by election year
│   └── economic/          # Economic indicator CSVs
├── graphs/                # Generated visualizations
└── reports/
    ├── nz_rules.md        # Laws of NZ Politics report
    ├── findings.md        # Initial analysis findings
    └── voter_flows.md     # Voter flow analysis report
```

## Usage

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Scrape data
python scraper.py          # Party vote polls
python pm_scraper.py       # Preferred PM polls
python economic_scraper.py # Economic indicators

# Run analyses
python analysis.py         # Initial 8-test analysis
python voter_flows.py      # Compositional voter flow analysis
python nz_rules.py         # Laws of NZ Politics (10 analyses)

# Generate visualizations
python visualize.py
```

## Dependencies

```
requests, beautifulsoup4, lxml   # Scraping
pandas, numpy                     # Data manipulation
matplotlib, seaborn               # Visualization
scipy, statsmodels                # Statistical analysis
```

## Data Sources

- **Polling Data**: Wikipedia opinion polling pages for NZ elections
- **Economic Data**: World Bank Open Data API (GDP, unemployment, CPI)
- **Events**: Manual compilation from news sources
