# Falcon Swing Options

A private, educational Streamlit workspace for studying U.S. market structure and options concepts. This project is for learning and paper-analysis only; it does not provide trade instructions or connect to a broker.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run app.py
```

Market data in the starter version is historical/delayed where available. Verify provider terms and timestamps before interpreting any chart. Options-chain coverage and Greeks require a dedicated data provider and are not simulated as live data here.

## Structure

- `app.py` — Streamlit interface
- `falcon/market.py` — market-data adapter
- `falcon/indicators.py` — transparent technical calculations
- `falcon/context.py` — broad-market context summary
- `falcon/scoring.py` — descriptive confluence score, not a probability or recommendation
- `tests/` — calculation tests

## Safety and limitations

No broker integration, order execution, personalized financial advice, or claims of predictive accuracy. Missing or stale data must be shown as unavailable, never silently substituted.
