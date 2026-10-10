<!-- fold: changelog -->
## CI: Full replay timeouts set from the first run, 2026-10-10

- The first manual Full replay on main (`a8cec13`, run 38074668402) passed in 110 minutes: Stage45-47 109, Stage54 65, Stage48 26, Stage63 20, live 16, tests 11, base 4, Stage39 3. Matrix `timeout-minutes` in `.github/workflows/full-replay.yml` now follow those durations (Stage45-47 165, Stage54 120, Stage48 60, Stage63 60, tests 45, live 40, base 30, Stage39 20); all stay under Verify's 180. No code, output or check changed.
