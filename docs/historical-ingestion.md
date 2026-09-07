# Stage 2 historical ingestion

Authorized years: 2008, 2011, 2014. General electorates are the primary output; national control tables may also include Māori electorate subtotals to make national reconciliation possible. No regression or forecasting is authorized.

Recovery found a clean branch at merged Stage 1 commit 8cf0345, with no unpushed code. One original browser-downloaded 2008 Auckland Central split-vote CSV survived in Downloads and has been imported unchanged with its actual file timestamp and SHA-256. Direct archive HTTP requests returned 403; normal browser downloads worked in the prior session. No cookies or browser credentials are extracted.

Acquisition: normal browser CSV link downloads → byte-preserving `scripts/ingest/historical_sources.py` import → data/sources.json. Reacquisition uses `--year YEAR --fetch-registered` and verifies expected checksums. If the server blocks a client, download the exact URL through a normal browser and import it; never save an error page as source data. Keep original byte encoding and line endings. Normalization belongs exclusively in scripts/transform/historical.py.

Split files inspected so far contain row totals plus two-decimal percentages, not exact cell counts. Parsed cells therefore carry reportedPercent and count:null. Do not round inferred counts and call them observations. General electorate result totals and national controls still need acquisition and validation at checkpoint A.

Source ownership and reuse: Electoral Commission archive, historical 2008 Chief Electoral Office publication. Crown copyright; accurate reproduction with source/copyright acknowledgement permitted under https://www.electionresults.govt.nz/about.html. No endorsement implied.
