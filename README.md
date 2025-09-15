# Operational Resilience Maturity Assessment (CMMI 1–5)

Production‑ready Streamlit app to **rate topics** and **visualise** aggregated results across **Dimensions** and **Themes** using only the provided dataset:
- `enhanced-operational-resilience-maturity-assessment.xlsx` (seed data)
- `app/utils/resilience_radar.py` (radar + mini‑bar plot helper)

## Stack
- Python 3.10+
- Streamlit (frontend), Plotly (charts)
- SQLAlchemy ORM + Alembic
- SQLite **or** MySQL 5.6‑compatible (PyMySQL driver)

## Quick start

### 1) Install (Poetry)
```bash
cd resilience_assessment_app
poetry install
poetry run python -V
```

### 2) Configure DB
Copy `.env.example` into `.streamlit/secrets.toml` (or edit directly). Choose backend:
```toml
[db]
backend = "sqlite"  # or "mysql"
```

For MySQL 5.6:
```toml
[db.mysql]
host = "localhost"
port = 3306
user = "resilience_user"
password = "your_password_here"
database = "resilience"
```

### 3) Create tables and seed
Either from the **sidebar** buttons in the app or via CLI:
```bash
# SQLite example
poetry run alembic upgrade head  # optional (app can create tables too)
poetry run python scripts/seed_dataset.py --backend sqlite --sqlite-path ./resilience.db --excel-path enhanced-operational-resilience-maturity-assessment.xlsx

# MySQL example
poetry run python scripts/seed_dataset.py --backend mysql --mysql-host localhost --mysql-port 3306 --mysql-user resilience_user --mysql-password '***' --mysql-db resilience --excel-path enhanced-operational-resilience-maturity-assessment.xlsx
```

### 4) Run
```bash
poetry run streamlit run streamlit_app.py
```

## UX
**Two‑page flow**:
1. **Rate topics** — filter by Dimension/Theme, view guidance per level, set CMMI with a slider, mark N/A, add comment. Sticky session header, live progress pill.
2. **Dashboard** — dimension scorecards (with coverage), radar chart with mini bars per theme (from `resilience_radar.py`), export JSON/XLSX.

## Project layout
```
app/
  domain/               # Entities/services (DDD)
  infrastructure/       # ORM, repos, UoW, DB wiring
  application/          # UI-facing API functions
  utils/                # resilience_radar.py
scripts/                # seed_dataset.py
alembic/                # migrations
streamlit_app.py        # entry
```

## Tests
```bash
poetry run pytest -q
```

## Scripts
Scripts are setup in pyproject.toml. Current scripts are:
poetry run lint app
poetry run format app
poetry run typecheck

## Notes / Assumptions
- Rating scale levels & labels are **derived from Excel column headers** (e.g., `1 Initial`, `2 Managed`, ...). No weights in the dataset → equal weighting.
- Multiple assessment sessions supported (name, assessor, organization, notes).
- Access control is out of scope for the MVP; add OIDC/SAML later if needed.
- If you rename columns/sheet, update `scripts/seed_dataset.py` accordingly.
```


### Combine sessions into a master session
In the sidebar, open **Sessions → Combine**. Select one or more source sessions and provide a name.  
The app creates a new session with **decimal per-topic scores** (stored as `computed_score`) computed as the mean of all available ratings across the selected sessions, excluding N/A.
