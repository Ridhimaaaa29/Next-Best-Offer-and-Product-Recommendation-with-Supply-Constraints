# Next-Best-Offer and Product Recommendation with Supply Constraints

A high-performance recommendation and decision engine that couples customer preference modeling with deterministic operational feasibility, inventory availability, and profit margin constraints.

---

## 🚀 Key Features
- **Separation of Concerns**: Unbiased customer propensity scoring decoupled from operational business constraints.
- **Strict Infeasibility Pruning**: Zero out-of-stock (`stock <= 0`), negative-margin (`margin < 10%`), or inactive products in final recommendations.
- **Explainable Decisions**: Score breakdowns and transparent exclusion reasons provided for every candidate product.
- **Dual Model Architecture**: Production-grade Gradient Boosting ML propensity scoring with fallback to deterministic heuristic weighting.
- **Enterprise REST API**: Built on FastAPI with strict Pydantic v2 schemas, X-Request-ID tracing, and structured logging.

---

## 📂 Repository Architecture
```text
next_best_offer/
├── data/                    # Datasets (raw, processed, synthetic)
├── notebooks/               # Jupyter notebooks for data understanding & evaluation
├── backend/app/             # FastAPI backend application
│   ├── api/                 # Routes and Pydantic schemas
│   ├── recommendation/      # Candidate generators, scoring models, policy engine
│   ├── domain/              # Business rules (inventory, margin, fulfilment)
│   ├── decision/            # Decision optimization and validation
│   ├── features/            # Feature engineering modules
│   ├── services/            # Application services
│   ├── db/                  # SQLAlchemy models and Neon connection
│   └── observability/       # Structured logging and metrics
├── frontend/                # Streamlit interactive demonstration UI
├── scripts/                 # CLI tools for preparation, training, and evaluation
├── docs/                    # Architecture and policy specifications
├── tests/                   # Unit, integration, API, decision, and evaluation tests
└── Dockerfile               # Containerization
```

---

## 🛠️ Quickstart

### 1. Installation (Windows PowerShell, F: drive)
```powershell
git clone https://github.com/Ridhimaaaa29/Next-Best-Offer-and-Product-Recommendation-with-Supply-Constraints.git
cd Next-Best-Offer-and-Product-Recommendation-with-Supply-Constraints
. .\scripts\use-f-drive.ps1
& .\.venv\Scripts\python.exe -m pip install --cache-dir .\.pip-cache -r .\requirements.txt
```

The project virtual environment and package/model caches are kept on `F:`. Do not
run the global `python` or `pip` commands for this project.

### 2. Configure Environment
Copy `.env.example` to `.env` and configure your database connection string:
```powershell
cp .env.example .env
```

### 3. Run FastAPI Backend
```powershell
& .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```
Interactive API docs: `http://localhost:8000/docs`

### 4. Run Frontend Streamlit UI
```powershell
& .\.venv\Scripts\python.exe -m streamlit run frontend\app.py
```

### 5. Run Test Suite
```powershell
& .\.venv\Scripts\python.exe -m pytest -v
```
