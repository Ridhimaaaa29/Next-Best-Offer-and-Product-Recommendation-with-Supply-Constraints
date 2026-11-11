# Known Limitations & Future Work
## Next-Best-Offer and Product Recommendation with Supply Constraints

### 1. Current Boundaries & Limitations
1. **Catalog Scale**:
   - The current production validation uses a synthetic 52-product catalog across 300 customers with 6,211 transactions. High-dimensional vector indexing (e.g. Milvus/HNSW) is planned for larger scales (>100k SKUs).
2. **Cold-Start Customers**:
   - New customers without prior interaction history fall back to category popularity and demographic segment baselines.
3. **Real-time Inventory Latency**:
   - Inventory checks execute synchronously against Neon PostgreSQL. For ultra-low latency (<5ms at scale), an in-memory cache (Redis/KeyDB) with CDC (Change Data Capture) will be required.
4. **Single-Node Optimization**:
   - Decision optimization uses the lightweight deterministic weighted decision engine over policy-feasible offers. Multi-item combinatorial basket constraints (e.g., maximum shipping box capacity) will benefit from dedicated integer programming solvers in a future phase.

---

### 2. Planned Iterations
* **Association Rules & Collaborative Filtering**: Matrix factorization (Implicit ALS) and basket mining stubs are defined in `backend/app/recommendation/`.
* **Agentic Explanations**: Natural language generative rationales for recommended offers (stubs in `backend/app/agents/`).
