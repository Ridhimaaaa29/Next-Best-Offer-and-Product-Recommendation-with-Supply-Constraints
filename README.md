# Next-Best-Offer and Product Recommendation with Supply Constraints

> **Enterprise-grade constraint-aware recommendation and decision platform** built with FastAPI, Streamlit, Gradient Boosting ML, Laya decision intelligence, MCP multi-agent orchestration, and Neon PostgreSQL.

---

## Problem Statement

Standard recommendation systems maximize relevance without considering whether a product can actually be delivered — leading to recommendations for items that are out of stock, below margin thresholds, or policy-ineligible. This project integrates operational supply constraints and formal business policy governance directly into the recommendation pipeline, ensuring every offer surfaced is genuinely actionable.

---

## Core Capabilities

| Capability | Description |
|---|---|
| **ML Propensity Scoring** | Gradient Boosting Classifier predicts customer-offer conversion probability (ROC-AUC 0.8583, PR-AUC 0.7094) |
| **Policy Engine** | Deterministic rule evaluation: stock availability, gross margin, product status, reward eligibility |
| **Laya Decision Intelligence** | `ModernBERT-large`-backed multi-objective decision engine selects the optimal feasible offer |
| **MCP Agentic Workflow** | 6-agent orchestration via Model Context Protocol — candidate generation through audit |
| **Inventory Dispatch** | Atomic stock deduction + audit record in a single PostgreSQL transaction with row-level locking |
| **Content-Based Similarity** | TF-IDF + cosine similarity engine for product-to-product recommendations |
| **Decision Audit Trail** | Full governance trace of every recommendation decision persisted to PostgreSQL |
| **10-Page Enterprise UI** | Streamlit frontend with consistent enterprise design system |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Streamlit Frontend                    │
│  10 pages · Enterprise CSS · Dark/Light theme tokens    │
└───────────────────────┬─────────────────────────────────┘
                        │ REST / JSON
┌───────────────────────▼─────────────────────────────────┐
│               FastAPI Backend  (/api/v1)                │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  ML Engine  │  │ Policy Engine│  │  Laya Adapter │  │
│  │ (GBC model) │→ │ (Rules 1–6)  │→ │ (ModernBERT)  │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
│                                           │             │
│  ┌────────────────────────────────────────▼──────────┐  │
│  │          MCP Multi-Agent Orchestration            │  │
│  │  Candidate Gen → Propensity → Policy →           │  │
│  │  Laya Decision → Audit → Response                │  │
│  └───────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────┘
                        │ SQLAlchemy (async-safe)
┌───────────────────────▼─────────────────────────────────┐
│          Neon PostgreSQL (7 tables + decision_audits)   │
│  customers · products · transactions · baskets ·        │
│  customer_product_interactions · operational_catalogue  │
│  · policy_rules · decision_audits                       │
└─────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | Streamlit 1.x · Custom enterprise CSS design system |
| **Backend API** | FastAPI · Uvicorn · Pydantic v2 |
| **ML Model** | Scikit-learn `GradientBoostingClassifier` · joblib persistence |
| **Decision Intelligence** | Laya `laya==0.4.26` · `ModernBERT-large` |
| **Multi-Agent** | Model Context Protocol (MCP) · AnyIO in-memory streams |
| **AI Assistant** | Groq API (`openai/gpt-oss-120b`) |
| **Database** | Neon PostgreSQL · SQLAlchemy ORM · Alembic migrations |
| **Containerization** | Docker · `docker-compose.aws.yml` (AWS EC2 deployment) |
| **Testing** | pytest · 101 unit tests (93 baseline + 8 dispatch atomicity) |

---

## ML Model Performance

Training on the synthetic Neon PostgreSQL dataset with strict out-of-time chronological splits:

| Metric | Value |
|---|---|
| **ROC-AUC (holdout)** | **0.8583** |
| **PR-AUC (holdout)** | **0.7094** |
| **5-Fold CV PR-AUC** | 0.7467 |
| **Brier Score** | 0.1143 (well-calibrated) |
| **Optimal Threshold** | τ* = 0.2522 |
| **Model** | Gradient Boosting · `lr=0.05, max_depth=5, n_estimators=50` |

**Recommendation Pipeline Comparison (K=5):**

| Pipeline | Precision@5 | Recall@5 | HitRate@5 | Policy Compliance |
|---|---|---|---|---|
| Popularity Baseline | 0.0464 | 0.0656 | 0.163 | 100% |
| Heuristic Pipeline | 0.1530 | 0.1921 | 0.489 | 100% |
| **ML Propensity Pipeline** | **0.1782** | **0.2245** | **0.541** | **100%** |

---

## MCP 6-Agent Workflow

The agentic recommendation flow executes 6 sequential agents over in-memory MCP streams:

1. **Candidate Generator** — Fetches unpurchased candidate products per customer
2. **Propensity Scorer** — Applies the trained GBC model for purchase probability
3. **Policy Validator** — Enforces 6 deterministic business rules (stock, margin, status)
4. **Laya Decision Engine** — Multi-objective ranking using `ModernBERT-large` embeddings
5. **Audit Writer** — Persists full decision trace to `decision_audits` table
6. **Response Formatter** — Structures the final NBO output with explanation codes

---

## Synthetic Dataset

| Table | Rows | Description |
|---|---|---|
| `customers` | 500 | Demographics, segments, membership tiers, lifetime spend |
| `products` | 52 | Master catalog with pricing, ratings, popularity |
| `transactions` | 6,211 | Line-item purchase history |
| `baskets` | 2,500 | Basket/order headers |
| `customer_product_interactions` | 2,100 | Aggregated recency, frequency, spend per customer-product pair |
| `operational_catalogue` | 52 | Real-time stock, margin, supplier, fulfillment data |
| `policy_rules` | 6 | Formal business constraint specifications |

> **Note:** Synthetic data was generated to provide verified operational constraints absent from real retail benchmarks (UCI Online Retail). Customer count in DB is 500; some early docs reference 300 — 500 is correct.

---

## Local Setup

### Prerequisites
- Python 3.11+
- PostgreSQL connection (Neon or local) — configure in `.env`
- Groq API key (for AI assistant feature)

### Installation

```bash
# Clone repository
git clone https://github.com/Ridhimaaaa29/Next-Best-Offer-and-Product-Recommendation-with-Supply-Constraints.git
cd Next-Best-Offer-and-Product-Recommendation-with-Supply-Constraints

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: set DATABASE_URL, GROQ_API_KEY
```

### Environment Variables (`.env`)

```env
DATABASE_URL=postgresql+psycopg2://user:password@host/dbname
GROQ_API_KEY=gsk_...
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
```

---

## Running the Application

```bash
# Terminal 1 — Start FastAPI backend
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 — Start Streamlit frontend
streamlit run frontend/app.py
```

- **Frontend:** http://localhost:8501
- **API Docs:** http://localhost:8000/docs
- **OpenAPI JSON:** http://localhost:8000/openapi.json

---

## Docker Deployment (AWS EC2)

```bash
# Build and run all services
docker-compose -f docker-compose.aws.yml up --build -d

# View logs
docker-compose -f docker-compose.aws.yml logs -f
```

---

## Running Tests

```bash
# Run all unit tests (101 tests)
.venv\Scripts\pytest.exe tests/unit/ -v

# Run only dispatch atomicity tests
.venv\Scripts\pytest.exe tests/unit/test_dispatch_atomicity.py -v

# Run with coverage
.venv\Scripts\pytest.exe tests/unit/ --cov=backend --cov-report=term-missing
```

> **Note:** Integration tests requiring live Neon DB may need `DATABASE_URL` set. The two `test_session_injection.py` async tests require running outside the sandbox (no socket restrictions).

---

## API Documentation

The full API contract is documented in [`docs/api_contract.md`](docs/api_contract.md).

**Key Endpoints:**

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/customers` | List customers |
| `GET` | `/api/v1/customers/{id}` | Customer profile |
| `GET` | `/api/v1/catalogue` | Operational catalogue with inventory |
| `POST` | `/api/v1/catalogue/{id}/dispatch` | **Atomic** inventory dispatch + audit |
| `POST` | `/api/v1/recommendations` | ML + policy + Laya NBO recommendation |
| `GET` | `/api/v1/recommendations/similar-products` | Content-based similarity |
| `POST` | `/api/v1/decisions/mcp-workflow` | 6-agent MCP workflow |
| `GET` | `/api/v1/decisions/history` | Decision audit trail |
| `POST` | `/api/v1/decisions/history` | Manual audit entry |
| `GET` | `/api/v1/analytics/summary` | Aggregated analytics |

---

## Project Documentation

| Document | Description |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | System architecture and component interaction |
| [`docs/api_contract.md`](docs/api_contract.md) | Full REST API specification with examples |
| [`docs/data_dictionary_and_assumptions.md`](docs/data_dictionary_and_assumptions.md) | Table schemas, field definitions, synthetic data assumptions |
| [`docs/decision_policy.md`](docs/decision_policy.md) | Business policy rules and constraint specification |
| [`docs/er_design_sql_clusters.md`](docs/er_design_sql_clusters.md) | Entity-relationship diagram and SQL cluster design |
| [`docs/known_limitations.md`](docs/known_limitations.md) | Current boundaries and future roadmap |
| [`data/synthetic/README.md`](data/synthetic/README.md) | Synthetic dataset generation methodology |
| [`reports/ml_model_evaluation.md`](reports/ml_model_evaluation.md) | ML experiment results, hyperparameter tuning, benchmark comparison |

---

## Repository

**GitHub:** https://github.com/Ridhimaaaa29/Next-Best-Offer-and-Product-Recommendation-with-Supply-Constraints
