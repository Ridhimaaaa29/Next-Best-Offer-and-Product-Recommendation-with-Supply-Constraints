# Decision & Policy Rules Specification
## Next-Best-Offer and Product Recommendation with Supply Constraints

### 1. Architectural Invariant
**Strict Decoupling of Preference Scoring and Supply Constraints**:
The scoring model predicts customer affinity/conversion propensity purely from historical preference features. The downstream Policy Engine evaluates operational feasibility and strictly filters out any non-compliant candidate before final ranking.

```
Zero infeasible products are permitted in the final recommendation set.
```

---

### 2. Hard Policy Constraints (Always Enforced)

| Rule ID | Name | Description | Violation Consequence |
| :--- | :--- | :--- | :--- |
| `RULE_STATUS_001` | Active Status | Product must have `product_status == 'active'` | Candidate is EXCLUDED |
| `RULE_STK_001` | Positive Stock | `available_stock` must be > 0 | Candidate is EXCLUDED |
| `RULE_STK_002` | Known Inventory | `available_stock` cannot be `NULL` and `inventory_status != 'unknown'` (fail-safe) | Candidate is EXCLUDED |
| `RULE_FRESH_001` | Fresh Operational Data | `data_freshness_status` must be verified/fresh (`verified_fresh`, `fresh`) | Candidate is EXCLUDED |
| `RULE_MAR_001` | Minimum Margin | `gross_margin_pct` must be >= 0.10 (10%) | Candidate is EXCLUDED |
| `RULE_DSC_001` | Discount Limit | When `requested_discount_pct` is supplied, must not exceed `max_discount_pct` | Candidate is EXCLUDED |

---

### 3. Contextual Policy Rules (Activated by Request Flags)

| Rule ID | Context Flag | Condition | Action |
| :--- | :--- | :--- | :--- |
| `RULE_REW_001` | `reward_context=True` | `reward_eligible == False` | Candidate is EXCLUDED |
| `RULE_PRO_001` | `promotion_context=True` | `promotion_eligible == False` | Candidate is EXCLUDED |
| `RULE_FUL_001` | `express_context=True` | `shipping_days > 7` | Flagged as warning in candidate metadata |

---

### 4. Deterministic Tie-Breaking
When multiple feasible candidates share identical recommendation scores, ordering is resolved deterministically by `product_id` in ascending alphabetical order (`x.product_id ASC`).
