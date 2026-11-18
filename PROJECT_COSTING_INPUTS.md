# Project Costing Input Report
**Project:** Next-Best-Offer and Product Recommendation with Supply Constraints  
**Repository:** `https://github.com/Ridhimaaaa29/Next-Best-Offer-and-Product-Recommendation-with-Supply-Constraints`  
**Audited Commit:** `6373f0d` (`main`)  
**Prepared As:** Read-Only Technical & Infrastructure Costing Audit  

> [!IMPORTANT]
> Repository files establish **software architecture, container topology, dependencies, storage footprints, and external service integrations**—they **do NOT establish actual cloud billing, discount tiers, free-tier eligibility, tax rates, or live consumption hours**. No AWS, Neon, or Groq monetary charges or usage hours have been fabricated below.

---

## Separation Framework

This report strictly separates evidence into three categories:
- **Section A — Verified Project Configuration:** Observed directly in repository configuration/source files (`Dockerfile.aws`, `docker-compose.aws.yml`, `backend/requirements-aws.txt`, `.env.aws.example`, `backend/app/config.py`, `backend/app/db/session.py`, `backend/app/api/routes/assistant.py`, `frontend/app.py`, disk measurements) and the recorded AWS EC2 deployment parameters supplied in the project brief.
- **Section B — Estimated Usage Assumptions:** Engineering baselines derived from container policies (`restart: unless-stopped`, 30-second healthchecks), measured disk footprints, and component behavior—explicitly **not** invoices.
- **Section C — Actual Billing Information Required from Cloud Dashboards:** Exact plan tiers, metered quantities, unit rates, and invoices that must be retrieved from **AWS**, **Neon**, and **Groq** dashboards.

---

## Part A — Verified Project Configuration (Technical Investigation 1–7)

### 1. AWS Resources Configured / Deployed for the Project
- **In Version-Controlled Repository Files (`Dockerfile.aws`, `docker-compose.aws.yml`, `backend/requirements-aws.txt`, `.env.aws.example`):**
  - Defines container build (`nbo-aws-full:latest`), runtime defaults (`APP_ENV=aws`, `LAYA_ENABLED=true`, `LAYA_PRELOAD_ON_STARTUP=true`, `LAYA_DEVICE=cpu`, `LAYA_CPU_BFLOAT16=false`, `LAYA_MAX_CANDIDATES=5`), single Uvicorn worker (`--workers 1`), two Compose services (`backend`, `frontend`), and persistent volume `nbo_laya_cache` targeting `8 GB RAM` x86/CPU hosts (`t3a.large` / `t3.large` / `m6i.large` noted in `docker-compose.aws.yml` comments).
  - **Repository does NOT contain:** Terraform/CloudFormation IaC, `nginx.conf`, Security Group JSON rules, Elastic IP allocation configs, ACM/TLS certificates, CloudWatch agents, or EC2 provisioning scripts.
- **AWS Host Configuration (Verified in Recorded Deployment Context):**
  - **Region:** `ap-southeast-2` (Sydney)
  - **Compute:** 1 × EC2 instance `m7i-flex.large` (`2` vCPU, `8 GiB` RAM, 64-bit x86, Ubuntu Server `24.04.5 LTS`)
  - **Block Storage:** 1 × EBS `30 GiB` `gp3` root volume (`3000 IOPS`, `125 MiB/s` throughput, encryption status to confirm against EBS console)
  - **Networking / Host Reverse Proxy:** Public IPv4 (`13.239.32.129`), Private IPv4 (`172.31.2.121`), Nginx reverse proxy listening on HTTP port `80` forwarding to Streamlit on `8501` (HTTPS/custom domain not configured; Security Group allows TCP `80` `0.0.0.0/0` and restricted `/32` SSH TCP `22`). Note: `docker-compose.aws.yml` maps `8000:8000` and `8501:8501`, so AWS Security Group enforcement keeps ports `8000`/`8501` closed publicly.

### 2. Docker Containers & Persistent Volumes (`docker-compose.aws.yml`)
1. **Container 1 — `nbo-backend-aws` (`nbo-aws-full:latest`, built from `Dockerfile.aws`):**
   - Runs `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 1` (`restart: unless-stopped`).
   - Serves FastAPI REST API, ML Gradient Boosting propensity scorer, in-memory AnyIO MCP 6-agent workflow, Groq assistant client, and CPU-only `LayaAdapter` singleton (`ModernBERT-large`, ~421M parameters).
   - Mounts volume `nbo_laya_cache` at `/app/.laya-cache`.
   - Healthcheck: `curl -fsS http://127.0.0.1:8000/api/v1/health` every `30s` (`start_period=180s`).
2. **Container 2 — `nbo-frontend-aws` (reuses `nbo-aws-full:latest`):**
   - Runs headless `streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true` (`restart: unless-stopped`).
   - Connects internally over Docker bridge via `API_BASE_URL=http://backend:8000/api/v1` (`depends_on: backend (condition: service_healthy)`).
   - Healthcheck: `curl -fsS http://127.0.0.1:8501/_stcore/health` every `30s` (`start_period=30s`).
3. **Named Persistent Docker Volume — `laya_cache` (host Docker volume name: `nbo_laya_cache`):**
   - Persists HuggingFace/Laya weights across container rebuilds/restarts so `HF_HUB_OFFLINE=1` prevents repeated model downloads.
   - Stored on the EC2 `30 GiB gp3` EBS root volume (no separate data EBS volume is configured in `docker-compose.aws.yml`).

### 3. Storage Requirements, Including Laya Model Cache (Directly Measured in Workspace)
- **Measured Application Code & Model Assets Copied by `Dockerfile.aws`:**
  - `backend/`: `689,099` bytes (~`0.66 MiB`)
  - `frontend/`: `231,958` bytes (~`0.22 MiB`)
  - `models/nbo_propensity_best_model.joblib`: `248,761` bytes (~`0.24 MiB`)
  - `data/synthetic/` (7 CSVs): `1,355,381` bytes (~`1.29 MiB`)
  - `reports/`: `59,584` bytes (~`0.06 MiB`)
  - **Subtotal source + ML + synthetic CSV assets:** **`2,584,783` bytes (~`2.47 MiB`)**
- **Measured Persistent Laya Weight Cache (`.laya-cache`, Mounted as `nbo_laya_cache:/app/.laya-cache`):**
  - Total `.laya-cache/` directory: **`846,361,170` bytes (~`807.15 MiB` / `0.79 GiB`)**
  - Includes `convaiinnovations/laya` snapshot (`model.safetensors` = `842,609,210` B, `tokenizer.json` = `3,583,228` B, plus encoder/RL configs).
- **Local-Only Artifacts Excluded from AWS Docker Image (`Dockerfile.aws.dockerignore`):**
  - `data/raw/` (`713,883,376` B), `data/processed/` (`19,254,694` B), legacy `data/nbo_database.sqlite` (`180,146,176` B), `.venv/`, `.pip-cache/`, `.hf-cache/`, `.env`. None of these consume EC2 Docker image space.
- **Total On-EC2 Storage Footprint Breakdown (Estimate Category):**
  - Ubuntu `24.04.5 LTS` base OS + Docker Engine + Nginx + system logs + `nbo-aws-full:latest` image (`python:3.11-slim`, `build-essential`, CPU `torch>=2.2.0`, `transformers`, `laya`, `scikit-learn`, `streamlit`, shared single image reused by both containers) + `~807 MiB` `nbo_laya_cache` Docker volume all reside inside the provisioned **`30 GiB gp3`** EBS root volume. Exact live `df -h` / `docker system df` usage on EC2 must be captured from the host (`[REQUIRES AUTHOR CONFIRMATION]`).

### 4. Database Service Dependencies & Plan Information (`backend/app/db/session.py`, `models.py`, `.env.aws.example`)
- **Service:** **Neon PostgreSQL** (cloud-managed serverless Postgres connected via `postgresql+psycopg://...` with `sslmode=require`).
- **ORM Schema Footprint (`models.py` + `alembic`):** 8 tables (`customers` 500 rows, `products` 52 rows, `operational_catalogue` 52 rows, `transactions` 7,466 rows, `baskets` 7,466 rows, `customer_product_interactions` 4,151 rows, `policy_rules` 7 rows, plus growing `decision_audits` audit logs). Base MVP relational seed CSVs total only `~1.29 MiB` on disk (`1,355,381` B).
- **Connection & Billing Behavior Implication:** `session.py` configures `pool_size=5`, `max_overflow=10`, `pool_pre_ping=True`, `pool_recycle=300`. Crucially, `docker-compose.aws.yml` runs **`/api/v1/health` every 30 seconds**, and `health.py:27` executes `SELECT 1` (`check_database_connection()`) against Neon on every health check.
  - **Cost/Quota Impact:** If Neon is configured with **scale-to-zero / auto-suspend**, a 30-second healthcheck running `SELECT 1` continuously prevents the Neon compute endpoint from suspending, resulting in **continuous active compute hours (up to ~730 hours/month)** while the backend container stays up!
- **Plan Info Available in Repository:** **None.** Neither `.env.aws.example`, `.env.example`, nor `config.py` stores Neon plan tier (`Free` vs `Launch` vs `Scale`), CU sizing, project region, or storage allowance (`.env` holds only the live `DATABASE_URL` string and was intentionally not inspected).

### 5. External API Dependencies & Commercial Model
1. **Groq API (`backend/app/api/routes/assistant.py`, `config.py`):**
   - **Endpoints used:** `GET https://api.groq.com/openai/v1/models` (`/assistant/status`) and `POST https://api.groq.com/openai/v1/chat/completions` (`/assistant/chat`).
   - **Model configured:** `openai/gpt-oss-120b` (`temperature=0.1`; up to `4000`-char question + serialized JSON context).
   - **Optionality:** Optional feature (`GROQ_API_KEY` can remain unset; system operates normally without it and disables only AI Assistant generation).
   - **Paid vs. Potentially Free:** Groq provides a free rate-limited tier as well as paid pay-as-you-go per-token pricing. Repository files do **not** show whether the active API key is on a Free developer tier or a Paid billing tier, nor monthly token counts.
2. **HuggingFace Hub (`huggingface_hub`, `laya`):**
   - Used **once** during cold startup if `/app/.laya-cache` lacks `model.safetensors` (`~807 MiB` download from public `convaiinnovations/laya` repo). Thereafter `HF_HUB_OFFLINE=1` disables Hub network fetches (`laya_adapter.py:255-256`).
   - **Cost:** Public HuggingFace weight download is **$0** (no HF Inference API / Pro subscription configured). AWS EC2 inbound data transfer from the internet is typically `$0` (verify against AWS billing).
3. **Browser-Side Assets (`frontend/app.py:39`):** Loads `Plus Jakarta Sans` from Google Fonts CDN in the end-user's browser (**$0** free public stylesheet).

### 6. Additional Cloud Services Check
- **`git grep` Verification Across Tracked Repository:** Confirmed **ZERO** code/config usage of:
  - AWS S3, RDS/Aurora, ElastiCache/Redis, CloudFront, Route 53, ALB/ELB, ECS/EKS/Fargate, Lambda, SQS/SNS, SES, CloudWatch exporter, or Secrets Manager.
  - Third-party SaaS: Twilio, SendGrid, Mailgun, Supabase, Firebase, OpenAI (direct), Anthropic, Pinecone/Milvus, or paid HuggingFace endpoints. *(The `Next-Best-Offer & Rewards` page explicitly runs a simulated in-app notification preview without any real SMS/email/push provider.)*
- **Non-AWS Backup Infrastructure Still Tracked in Repo:**
  - `Dockerfile` and `docker-compose.yml` remain in git as an independent lightweight **Render** backup deployment (`APP_ENV=render`, `PORT=10000`, Laya disabled). Unless an active Render web service is still deployed in parallel, Render incurs `$0` (`[REQUIRES AUTHOR CONFIRMATION]`).

### 7. Relationship of Streamlit Community Cloud (`https://nbo-recommendation-engine.streamlit.app/`)
- **Repository Git Evidence:**
  - Commit `a57698f` (`Update requirements.txt with streamlit and requests for Streamlit Community Cloud deployment`) and commit `bc57ea7` (`Added Dev Container Folder` targeting `streamlit run frontend/app.py`) document an **earlier standalone Streamlit frontend deployment**.
  - In the current AWS deployment (`docker-compose.aws.yml`), the active frontend is **not** Streamlit Community Cloud—it is the self-hosted **`nbo-frontend-aws` Docker container** running on the EC2 instance (`http://13.239.32.129` -> Nginx port `80` -> `127.0.0.1:8501` -> `http://backend:8000/api/v1`).
- **Costing Impact:** Streamlit Community Cloud public hosting is free (`$0`), and because it is an earlier deployment rather than the primary AWS stack, it adds **$0 AWS/infra cost** (confirm in dashboard whether it is retired/sleeping or still kept active for demo purposes).

---

## Part B — Estimated Monthly Infrastructure Usage Assumptions (Item 8)

> [!NOTE]
> The figures below are **operational usage assumptions** derived from container configuration (`restart: unless-stopped`, 30s healthchecks, measured file sizes) for planning a costing worksheet. **They are NOT verified billing invoices.**

- **Time Horizon Basis:** Standard 1-month calendar window = **`730` hours** (or `720`–`744` hours depending on exact AWS billing month).
- **Assumed EC2 Operating Schedule (Requires Author Decision for Final Sheet):**
  - *Scenario 1 — Always-On (`24×7`):* **`730` hours/month** (matches `restart: unless-stopped` production availability).
  - *Scenario 2 — Part-Time / Demo Schedule:* e.g., `8 hours/day × 30 days = 240 hours/month` or on-demand start/stop during evaluation (`EBS 30 GiB gp3` still bills `730` hrs/month even when EC2 is stopped!).
- **EBS Root Volume:** `30 GiB` provisioned continuously (`1 GB-month × 30` = `30 GiB-months`, baseline `3000 IOPS` and `125 MiB/s` gp3 throughput—check AWS `ap-southeast-2` pricing for whether baseline 3000 IOPS / 125 MiB/s is included at $0 surcharge).
- **AWS Network / Public IPv4 & Egress:**
  - `1` Public IPv4 address attached while instance runs (`730` IP-hours/month under 24×7; confirm AWS Public IPv4 hourly charge since Feb 2024 vs Free Tier).
  - Outbound Internet Egress: Minimal HTTP HTML/JSON/WebSocket Streamlit UI traffic during demo/testing (**author must confirm real GB transferred in Cost Explorer**; likely `< 5–10 GiB/month` for demo/evaluation traffic).
- **Neon PostgreSQL Compute & Storage:**
  - Storage: Initial seed (`~1.29 MiB` CSVs) + indexes + `decision_audits` JSON rows -> estimated `< 0.1–0.5 GiB` logical DB storage (confirm actual Neon branch storage + WAL history).
  - Compute Active Hours: **Crucial assumption check** — because backend `HEALTHCHECK` runs `SELECT 1` every `30s`, compute hours will match **backend uptime hours** (up to `730` CU-hours/month × active vCPU/CU size, e.g., `0.25`–`1` CU depending on Neon endpoint size) unless healthchecks were paused or EC2 was stopped.
- **Groq API Tokens:**
  - Payload per question: `SYSTEM_PROMPT` (~250–300 tokens) + untrusted JSON `context` (~300–1,500 tokens depending on candidates/audit payload) + `question` (`<= 4,000` chars) + assistant answer (~150–500 tokens) = roughly **`~800–2,500` total tokens per chat turn**; status checks (`GET /models`) consume `0` inference tokens. Exact monthly token total depends strictly on actual test/user query volume (`[REQUIRES AUTHOR CONFIRMATION]`).

---

## Master Costing Input Table

| Resource / Service | Configuration | Quantity | Unit | Estimated Monthly Usage | Pricing Source Required | Actual Cost Available? (Yes/No) | Missing Information |
|---|---|---:|---|---|---|---|---|
| **AWS EC2 Compute** (`NBO-Laya-Production`) | `m7i-flex.large`, 2 vCPU, 8 GiB RAM, Linux (Ubuntu 24.04.5 LTS), `ap-southeast-2` (Sydney), 64-bit x86 | 1 | Instance | Up to `730` hrs/mo (24×7) *or* actual demo running hours | AWS EC2 Pricing (`ap-southeast-2` On-Demand / Free Tier / Savings Plan) | **No** | Exact running hours/mo, purchase option (On-Demand vs Free/Credits), AWS Cost Explorer EC2 line item |
| **AWS EBS Block Storage** | `30 GiB` `gp3`, `3000 IOPS`, `125 MiB/s` throughput (`ap-southeast-2`), holds OS + Docker + `~807 MiB` Laya volume | 30 | GiB-month | `30 GiB` provisioned `24×7` (`730` hrs/mo) | AWS EBS `gp3` Pricing (`ap-southeast-2`) | **No** | Confirmation of encryption status, snapshot count/GB (if any EBS snapshots exist), exact AWS EBS invoice |
| **AWS Public IPv4 Address** | Public IP `13.239.32.129` attached to EC2 instance | 1 | IPv4-hour | Up to `730` IP-hrs/mo (24×7) or running hrs | AWS VPC Public IPv4 Address Pricing | **No** | Whether covered by AWS Free Tier/credits or billed at standard IPv4 hourly rate; Elastic IP idle hours if allocated |
| **AWS Data Transfer (Egress)** | Outbound HTTP responses (Nginx port `80` -> Streamlit/API JSON) to internet (`0.0.0.0/0`); Inbound (`~807 MiB` HF weights, pip packages) typically `$0` | Variable | GiB transferred out | Demo/testing dependent (unmeasured in repo) | AWS Data Transfer Out Pricing (`ap-southeast-2`) + AWS Free Tier (`100 GB` shared check) | **No** | Actual monthly GB egress & cross-AZ/region bytes from AWS Billing / Cost Explorer |
| **Nginx Reverse Proxy & Docker Compose** | Ubuntu `nginx` service (port `80 -> 8501`) + Docker Engine (`nbo-backend-aws` & `nbo-frontend-aws` sharing `nbo-aws-full:latest`) | 1 / 2 | Host proxy / Containers | Runs co-located on the `m7i-flex.large` EC2 OS | Open-source software (`$0` license cost; compute already counted in EC2) | **Yes (`$0` software license)** | Confirmation that Nginx config adds no paid modules; live `df -h` / `docker system df` on EC2 |
| **Laya Model (`ModernBERT-large`)** | `laya==0.4.26` (`convaiinnovations/laya`), ~421M params, CPU FP32, `model.safetensors` `842.6 MB`, persistent volume `nbo_laya_cache` (`~807 MiB`) | 1 | Model weight cache | Runs locally on EC2 CPU (no external API token charge); cached offline after 1st pull | Open-source/hosted compute (`$0` per-inference API fee; uses EC2 CPU/RAM/EBS) | **Yes (`$0` direct API/license fee)** | Verification of license terms on `convaiinnovations/laya` if commercial distribution is planned |
| **Neon PostgreSQL Database** | Managed serverless Postgres (`sslmode=require`, `psycopg` pool `5+10`, 8 tables, `~1.29 MiB` seed data; `SELECT 1` every `30s` by backend healthcheck) | 1 | Neon Project / DB Branch | Storage `< 0.5 GiB` est.; Compute up to `730` active hrs/mo if 30s healthcheck keeps endpoint awake | Neon Pricing Dashboard (Free vs Launch vs Scale CU-hr & GiB-month rates) | **No** | Exact Neon plan tier, Neon cloud region, min/max CU setting, actual CU-hours, storage GiB, branch/written data metrics |
| **Groq AI Assistant API** | `https://api.groq.com/openai/v1`, model `openai/gpt-oss-120b` (`temperature=0.1`), optional assistant chat & model check | Variable | 1M Input / Output Tokens | Usage-dependent (`~800–2,500` tokens/chat turn est.) | Groq Cloud Pricing & Developer Console Usage | **No** | Groq plan status (Free tier vs Paid On-Demand), actual monthly prompt tokens + completion tokens + spend |
| **HuggingFace Hub Weight Fetch** | One-time public pull of `convaiinnovations/laya` into `/app/.laya-cache` (`HF_HUB_OFFLINE=1` afterwards) | 1 | One-time pull (`~807 MiB`) | Initial volume seed only | HuggingFace Hub (public download `$0`) | **Yes (`$0` HF service charge)** | None (no paid HF Inference Endpoint configured) |
| **Render Backup Deployment** *(if stopped/unused)* | `Dockerfile` / `docker-compose.yml` lightweight fallback (`APP_ENV=render`, Laya disabled) | 0–1 | Service | Backup config only in git | Render Dashboard (only if a live Render service exists) | **No** | Confirmation from author whether Render backup service is deleted/suspended (`$0`) or active |
| **Streamlit Community Cloud** *(earlier frontend)* | `https://nbo-recommendation-engine.streamlit.app/` (`a57698f` / `bc57ea7`); superseded by EC2 container in AWS stack | 0–1 | App | Earlier deployment (`$0` Community tier if still live) | Streamlit Community Cloud | **No** | Confirmation whether still active (`$0` Community tier) or decommissioned |

---

## Part C — Exact Dashboards, Screenshots & Billing Exports Needed to Complete the Costing Sheet

Collect the following exports/screenshots directly from your live cloud consoles (ensure secrets/connection strings/account IDs are masked before embedding in reports):

### 1. AWS Billing & EC2 Console (`ap-southeast-2`)
1. **AWS Billing & Cost Management -> Bills / Cost Explorer (Month-to-Date & Prior Month):**
   - Screenshot or CSV export grouped by **Service** and **Usage Type** showing exact line items for `EC2 - Other` (EBS `gp3`, Data Transfer, Public IPv4), `Amazon Elastic Compute Cloud` (`m7i-flex.large` `BoxUsage`), and any AWS Free Tier / Promotional Credits applied.
2. **EC2 Console -> Instances -> `NBO-Laya-Production` Summary & Storage Tabs:**
   - Confirms exact 17-character Instance ID, launch time / uptime state, root volume ID, exact `30 GiB gp3` / `3000 IOPS` / `125 MiB/s`, and **Encrypted (`Yes`/`No`)** status.
3. **EC2 Console -> Elastic Block Store -> Snapshots (and Elastic IPs):**
   - Confirms `0` snapshots/EIPs (or captures any extra snapshot GiB / idle EIP charges).
4. **EC2 Host Verification (`ssh` terminal):**
   - Output of `df -h` and `docker system df` (showing exact used GB on `/` and `nbo_laya_cache` volume size).

### 2. Neon Console (`console.neon.tech`)
5. **Neon Billing / Usage Dashboard Screenshot + CSV (if available):**
   - Shows current **Plan** (Free / Launch / Scale), **Region**, **Active Compute Time (CU-hours)**, **Storage (GiB-months)**, **Data Transfer**, and **Written Data**, plus confirm **Auto-suspend / Scale-to-zero** settings (important because the 30-second Docker healthcheck keeps DB active).

### 3. Groq Cloud Console (`console.groq.com`)
6. **Groq Usage / Billing Page Screenshot:**
   - Shows **Tier** (Free vs Paid Developer/On-Demand), **Input & Output Token Counts** for `openai/gpt-oss-120b`, total API requests, and accrued dollar amount (`$0.00` or metered charge).

### 4. Secondary / Earlier Hosts (Confirm `$0` / Inactive Status)
7. **Render Dashboard (`dashboard.render.com`) & Streamlit Cloud (`share.streamlit.io`):**
   - Screenshot or confirmation showing the Render backup service is deleted/free/inactive (`$0`) and whether `https://nbo-recommendation-engine.streamlit.app/` is retired or on the `$0` Community tier.

