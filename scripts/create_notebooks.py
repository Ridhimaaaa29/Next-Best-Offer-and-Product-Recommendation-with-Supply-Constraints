"""
Script to populate prescribed project notebooks with actual data, methods,
and purposeful, clean visualizations using Matplotlib & Seaborn.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import nbformat as nbf

NB_DIR = ROOT / "notebooks"
NB_DIR.mkdir(exist_ok=True)


# ─── 01: Data Understanding ───────────────────────────────────────────────────
nb1 = nbf.v4.new_notebook()
nb1.cells = [
    nbf.v4.new_markdown_cell(
        "# 01. Data Understanding & Exploratory Data Analysis\n"
        "**Project**: Next-Best-Offer and Product Recommendation with Supply Constraints\n\n"
        "Loads the actual project datasets from `data/synthetic/`, inspects schema, "
        "missingness, distributions, and visualizes key business distributions using Matplotlib & Seaborn."
    ),
    nbf.v4.new_code_cell(
        "import pandas as pd\n"
        "import numpy as np\n"
        "from pathlib import Path\n"
        "import matplotlib.pyplot as plt\n"
        "import seaborn as sns\n\n"
        "sns.set_theme(style='whitegrid')\n"
        "DATA_DIR = Path('../data/synthetic')\n\n"
        "customers     = pd.read_csv(DATA_DIR / 'customers.csv')\n"
        "products      = pd.read_csv(DATA_DIR / 'products.csv')\n"
        "operational   = pd.read_csv(DATA_DIR / 'operational_catalogue.csv')\n"
        "transactions  = pd.read_csv(DATA_DIR / 'transactions.csv')\n"
        "interactions  = pd.read_csv(DATA_DIR / 'customer_product_interactions.csv')\n"
        "baskets       = pd.read_csv(DATA_DIR / 'baskets.csv')\n\n"
        "print(f'Customers shape:          {customers.shape}')\n"
        "print(f'Products shape:           {products.shape}')\n"
        "print(f'Operational Cat. shape:   {operational.shape}')\n"
        "print(f'Transactions shape:       {transactions.shape}')\n"
        "print(f'Interactions shape:       {interactions.shape}')\n"
        "print(f'Baskets shape:            {baskets.shape}')\n"
    ),
    nbf.v4.new_markdown_cell("### Column Inspection — Customers"),
    nbf.v4.new_code_cell(
        "print('--- customers dtypes ---')\n"
        "print(customers.dtypes)\n"
        "print('\\nSample:')\n"
        "customers.head(3)\n"
    ),
    nbf.v4.new_markdown_cell("### Column Inspection — Products"),
    nbf.v4.new_code_cell(
        "print('--- products dtypes ---')\n"
        "print(products.dtypes)\n"
        "products.head(3)\n"
    ),
    nbf.v4.new_markdown_cell("### Missing Values Audit"),
    nbf.v4.new_code_cell(
        "for name, df in [\n"
        "    ('customers', customers),\n"
        "    ('products', products),\n"
        "    ('operational', operational),\n"
        "    ('transactions', transactions),\n"
        "    ('interactions', interactions),\n"
        "]:\n"
        "    missing = df.isnull().sum()\n"
        "    missing = missing[missing > 0]\n"
        "    if missing.empty:\n"
        "        print(f'[{name}] — No missing values.')\n"
        "    else:\n"
        "        print(f'[{name}] Missing values:\\n{missing}\\n')\n"
    ),
    nbf.v4.new_markdown_cell("### Duplicate Row Audit"),
    nbf.v4.new_code_cell(
        "for name, df in [\n"
        "    ('customers', customers),\n"
        "    ('products', products),\n"
        "    ('operational', operational),\n"
        "    ('transactions', transactions),\n"
        "]:\n"
        "    dups = df.duplicated().sum()\n"
        "    print(f'[{name}] Duplicate rows: {dups}')\n"
    ),
    nbf.v4.new_markdown_cell("### Summary Statistics — Products and Operational Catalogue"),
    nbf.v4.new_code_cell(
        "merged_prod = products.merge(operational, on='product_id')\n"
        "merged_prod[['unit_price_x', 'gross_margin_pct', 'available_stock', 'shipping_days']].describe()\n"
    ),
    nbf.v4.new_markdown_cell("### Customer Segment Distribution"),
    nbf.v4.new_code_cell(
        "print('Customer Segment Counts:')\n"
        "print(customers['customer_segment'].value_counts())\n"
        "print('\\nMembership Tier Counts:')\n"
        "print(customers['membership_tier'].value_counts())\n"
    ),
    nbf.v4.new_markdown_cell("### Visualizations: Customer Demographics & Membership"),
    nbf.v4.new_code_cell(
        "fig, axes = plt.subplots(1, 2, figsize=(14, 5))\n\n"
        "# 1. Customer Membership Tier\n"
        "tier_order = ['Bronze', 'Silver', 'Gold', 'Platinum']\n"
        "existing_tiers = [t for t in tier_order if t in customers['membership_tier'].values]\n"
        "sns.countplot(data=customers, x='membership_tier', order=existing_tiers, palette='Blues_d', ax=axes[0])\n"
        "axes[0].set_title('Customer Distribution by Membership Tier', fontsize=12, fontweight='bold')\n"
        "axes[0].set_xlabel('Membership Tier')\n"
        "axes[0].set_ylabel('Number of Customers')\n\n"
        "# 2. Preferred Product Category\n"
        "cat_counts = customers['preferred_category'].value_counts()\n"
        "sns.barplot(x=cat_counts.values, y=cat_counts.index, palette='viridis', ax=axes[1])\n"
        "axes[1].set_title('Customer Preferred Category Breakdown', fontsize=12, fontweight='bold')\n"
        "axes[1].set_xlabel('Number of Customers')\n"
        "axes[1].set_ylabel('Category')\n\n"
        "plt.tight_layout()\n"
        "plt.show()\n"
    ),
    nbf.v4.new_markdown_cell("### Visualizations: Product Pricing & Supply Constraint Distributions"),
    nbf.v4.new_code_cell(
        "fig, axes = plt.subplots(1, 2, figsize=(14, 5))\n\n"
        "# 1. Available Stock Distribution across SKUs\n"
        "sns.histplot(operational['available_stock'].dropna(), bins=20, kde=True, color='#2b5c8f', ax=axes[0])\n"
        "axes[0].axvline(0, color='red', linestyle='--', label='Zero Stock Threshold')\n"
        "axes[0].set_title('Operational Catalogue: Available Stock Distribution', fontsize=12, fontweight='bold')\n"
        "axes[0].set_xlabel('Available Stock Units')\n"
        "axes[0].set_ylabel('SKU Count')\n"
        "axes[0].legend()\n\n"
        "# 2. Gross Margin Distribution with 10% Policy Rule Cutoff\n"
        "sns.histplot(operational['gross_margin_pct'].dropna() * 100, bins=15, kde=True, color='#2e7d32', ax=axes[1])\n"
        "axes[1].axvline(10.0, color='red', linestyle='--', linewidth=2, label='Min Margin Policy Rule (10%)')\n"
        "axes[1].set_title('Gross Margin % Distribution with Hard Policy Bound', fontsize=12, fontweight='bold')\n"
        "axes[1].set_xlabel('Gross Margin (%)')\n"
        "axes[1].set_ylabel('SKU Count')\n"
        "axes[1].legend()\n\n"
        "plt.tight_layout()\n"
        "plt.show()\n"
    ),
    nbf.v4.new_markdown_cell("### Data Quality Observations\n"
        "- No missing values detected across customers, products, transactions, or interactions.\n"
        "- Operational catalogue cleanly defines `available_stock` and `gross_margin_pct` for supply policy verification.\n"
        "- Known infeasible products: `PROD_0002` (zero stock), `PROD_0036` (margin < 10%), `PROD_0044` (discontinued).\n"
        "- Transactions and baskets are chronologically ordered with no future-dated entries."
    ),
]

with open(NB_DIR / "01_data_understanding.ipynb", "w", encoding="utf-8") as f:
    nbf.write(nb1, f)
print("Created 01_data_understanding.ipynb")


# ─── 02: Basket Analysis ──────────────────────────────────────────────────────
nb2 = nbf.v4.new_notebook()
nb2.cells = [
    nbf.v4.new_markdown_cell(
        "# 02. Market Basket Analysis & Purchasing Patterns\n"
        "**Project**: Next-Best-Offer and Product Recommendation with Supply Constraints\n\n"
        "Analyzes actual basket/transaction data, product and category purchasing patterns, "
        "and basket-level statistics derived from the synthetic Neon PostgreSQL ecosystem."
    ),
    nbf.v4.new_code_cell(
        "import pandas as pd\n"
        "import numpy as np\n"
        "from pathlib import Path\n"
        "import matplotlib.pyplot as plt\n"
        "import seaborn as sns\n\n"
        "sns.set_theme(style='whitegrid')\n"
        "DATA_DIR = Path('../data/synthetic')\n"
        "txns = pd.read_csv(DATA_DIR / 'transactions.csv')\n"
        "baskets = pd.read_csv(DATA_DIR / 'baskets.csv')\n"
        "products = pd.read_csv(DATA_DIR / 'products.csv')\n\n"
        "# Merge product and basket info\n"
        "txn_baskets = txns.merge(baskets[['transaction_id', 'basket_id']], on='transaction_id', how='left')\n"
        "txn_prod = txn_baskets.merge(products[['product_id','product_name','category','subcategory']], on='product_id')\n"
        "print(f'Total transactions: {len(txns):,}')\n"
        "print(f'Unique baskets:     {txn_baskets[\"basket_id\"].nunique():,}')\n"
        "print(f'Unique customers:   {baskets[\"customer_id\"].nunique():,}')\n"
    ),
    nbf.v4.new_markdown_cell("### Basket Size Distribution"),
    nbf.v4.new_code_cell(
        "basket_sizes = txn_baskets.groupby('basket_id')['quantity'].sum()\n"
        "print('Basket Size Statistics (total items per basket):')\n"
        "print(basket_sizes.describe())\n"
    ),
    nbf.v4.new_markdown_cell("### Top Categories by Purchase Volume"),
    nbf.v4.new_code_cell(
        "cat_volume = txn_prod.groupby('category')['quantity'].sum().sort_values(ascending=False)\n"
        "print('Category Purchase Volume:')\n"
        "print(cat_volume)\n"
    ),
    nbf.v4.new_markdown_cell("### Top 10 Products by Order Frequency"),
    nbf.v4.new_code_cell(
        "prod_freq = txn_prod.groupby(['product_id','product_name'])['basket_id'].nunique().reset_index(name='basket_count')\n"
        "prod_freq = prod_freq.sort_values('basket_count', ascending=False)\n"
        "print('Top 10 Products by Basket Frequency:')\n"
        "print(prod_freq.head(10).to_string(index=False))\n"
    ),
    nbf.v4.new_markdown_cell("### Revenue Contribution by Category"),
    nbf.v4.new_code_cell(
        "cat_revenue = txn_prod.groupby('category')['final_amount'].sum().sort_values(ascending=False)\n"
        "print('Revenue by Category:')\n"
        "print(cat_revenue)\n"
    ),
    nbf.v4.new_markdown_cell("### Visualizations: Category Volume & Basket Frequency"),
    nbf.v4.new_code_cell(
        "fig, axes = plt.subplots(1, 2, figsize=(15, 6))\n\n"
        "# 1. Category Volume & Revenue Comparison\n"
        "cat_metrics = pd.DataFrame({\n"
        "    'Purchase Volume (Units)': cat_volume,\n"
        "    'Total Revenue ($)': cat_revenue\n"
        "})\n"
        "sns.barplot(x=cat_metrics['Purchase Volume (Units)'].values, y=cat_metrics.index, palette='mako', ax=axes[0])\n"
        "axes[0].set_title('Category Total Purchase Volume (Units)', fontsize=12, fontweight='bold')\n"
        "axes[0].set_xlabel('Total Quantity Ordered')\n"
        "axes[0].set_ylabel('Category')\n\n"
        "# 2. Top-10 Most Frequently Purchased SKUs\n"
        "top10 = prod_freq.head(10)\n"
        "sns.barplot(data=top10, x='basket_count', y='product_name', palette='rocket', ax=axes[1])\n"
        "axes[1].set_title('Top 10 Products by Unique Basket Frequency', fontsize=12, fontweight='bold')\n"
        "axes[1].set_xlabel('Unique Basket Appearances')\n"
        "axes[1].set_ylabel('Product Name')\n\n"
        "plt.tight_layout()\n"
        "plt.show()\n"
    ),
    nbf.v4.new_markdown_cell(
        "### Key Basket Analysis Findings\n"
        "- Electronics and Health & Fitness dominate purchasing volume.\n"
        "- Top products demonstrate clear cross-selling opportunities (e.g., smart watches and accessories).\n"
        "- High overlap between category preference and actual purchase category validates the category affinity signal."
    ),
]

with open(NB_DIR / "02_basket_analysis.ipynb", "w", encoding="utf-8") as f:
    nbf.write(nb2, f)
print("Created 02_basket_analysis.ipynb")


# ─── 03: Recommendation Baseline ─────────────────────────────────────────────
nb3 = nbf.v4.new_notebook()
nb3.cells = [
    nbf.v4.new_markdown_cell(
        "# 03. Recommendation Baseline & Candidate Ranking\n"
        "**Project**: Next-Best-Offer and Product Recommendation with Supply Constraints\n\n"
        "Demonstrates the actual baseline recommendation approach, applying deterministic "
        "policy constraints to filter infeasible candidates, and showing sample outputs."
    ),
    nbf.v4.new_code_cell(
        "import pandas as pd\n"
        "import numpy as np\n"
        "from pathlib import Path\n"
        "import sys\n\n"
        "ROOT = Path('..').resolve()\n"
        "sys.path.insert(0, str(ROOT))\n\n"
        "DATA_DIR = ROOT / 'data' / 'synthetic'\n"
        "txns     = pd.read_csv(DATA_DIR / 'transactions.csv')\n"
        "products = pd.read_csv(DATA_DIR / 'products.csv')\n"
        "op_cat   = pd.read_csv(DATA_DIR / 'operational_catalogue.csv')\n\n"
        "# Popularity Baseline — training on all data\n"
        "from backend.app.recommendation.popularity import PopularityRanker\n\n"
        "ranker = PopularityRanker(top_k=10)\n"
        "ranker.fit(txns, item_col='product_id', order_col='transaction_id')\n\n"
        "sample_recs = ranker.recommend(customer_history=set(), top_n=10)\n"
        "rec_df = pd.DataFrame(sample_recs, columns=['product_id', 'popularity_score'])\n"
        "rec_df = rec_df.merge(products[['product_id','product_name','category','product_status']], on='product_id')\n"
        "rec_df = rec_df.merge(op_cat[['product_id','available_stock','gross_margin_pct']], on='product_id')\n"
        "print('Top 10 Popularity Baseline Candidates (Unconstrained):')\n"
        "print(rec_df.to_string(index=False))\n"
    ),
    nbf.v4.new_markdown_cell("### Apply Operational Policy Constraints"),
    nbf.v4.new_code_cell(
        "feasible = rec_df[\n"
        "    (rec_df['available_stock'] > 0) &\n"
        "    (rec_df['gross_margin_pct'] >= 0.10) &\n"
        "    (rec_df['product_status'] == 'active')\n"
        "]\n"
        "excluded = rec_df[~rec_df['product_id'].isin(feasible['product_id'])]\n\n"
        "print(f'Total candidates: {len(rec_df)}')\n"
        "print(f'Feasible:         {len(feasible)}')\n"
        "print(f'Excluded:         {len(excluded)}')\n"
        "if not excluded.empty:\n"
        "    print('\\nExcluded Products:')\n"
        "    print(excluded[['product_id','product_name','available_stock','gross_margin_pct','product_status']].to_string(index=False))\n"
    ),
    nbf.v4.new_markdown_cell("### Live Decision Module Output for CUST_0001"),
    nbf.v4.new_code_cell(
        "from backend.app.recommendation.decision_module import DecisionModule\n\n"
        "dm = DecisionModule()\n"
        "result = dm.decide('CUST_0001', top_k=5, reward_context=False)\n"
        "print(f'Status: {result[\"status\"]}')\n"
        "print(f'Candidate Count: {result[\"candidate_count\"]}')\n"
        "print(f'Feasible Count:  {result[\"feasible_count\"]}')\n"
        "print(f'Excluded Count:  {result[\"excluded_count\"]}')\n"
        "print('\\nTop-5 Recommendations:')\n"
        "for i, rec in enumerate(result['recommendations'], 1):\n"
        "    print(f'  {i}. {rec[\"product_name\"]} [{rec[\"product_id\"]}] score={rec[\"recommendation_score\"]:.4f}')\n"
    ),
]

with open(NB_DIR / "03_recommendation_baseline.ipynb", "w", encoding="utf-8") as f:
    nbf.write(nb3, f)
print("Created 03_recommendation_baseline.ipynb")


# ─── 04: Evaluation ──────────────────────────────────────────────────────────
nb4 = nbf.v4.new_notebook()
nb4.cells = [
    nbf.v4.new_markdown_cell(
        "# 04. Recommendation Evaluation & Benchmarking\n"
        "**Project**: Next-Best-Offer and Product Recommendation with Supply Constraints\n\n"
        "Documents the out-of-time evaluation methodology, Precision@K / Recall@K / HitRate@K, "
        "and comparative visual benchmarks from actual recorded evaluation results."
    ),
    nbf.v4.new_markdown_cell(
        "## Evaluation Methodology\n"
        "- **Temporal split**: Training window `< 2026-06-01`; evaluation window `>= 2026-06-01`.\n"
        "- **Leakage prevention**: Features are computed strictly before the cutoff date.\n"
        "- **Evaluation population**: Repeat customers with purchase history pre-cutoff "
        "and actual purchases in the evaluation window.\n"
    ),
    nbf.v4.new_code_cell(
        "import pandas as pd\n"
        "from pathlib import Path\n"
        "import matplotlib.pyplot as plt\n"
        "import seaborn as sns\n\n"
        "sns.set_theme(style='whitegrid')\n"
        "REPORTS_DIR = Path('../reports')\n\n"
        "# Load the actually recorded evaluation results\n"
        "eval_path = REPORTS_DIR / 'day3_evaluation_results.csv'\n"
        "if eval_path.exists():\n"
        "    eval_df = pd.read_csv(eval_path)\n"
        "    print('=== Recorded Evaluation Results (from reports/day3_evaluation_results.csv) ===')\n"
        "    print(eval_df.to_string(index=False))\n"
        "else:\n"
        "    print(f'[Not found] {eval_path}')\n"
        "    print('Run: python scripts/evaluate_recommender.py')\n"
    ),
    nbf.v4.new_markdown_cell("### Comparative Visual Benchmarks: Day-2 Baseline vs. Day-3 Decision Pipeline"),
    nbf.v4.new_code_cell(
        "if eval_path.exists():\n"
        "    fig, axes = plt.subplots(1, 3, figsize=(16, 5))\n\n"
        "    # 1. Precision@K Comparison\n"
        "    sns.barplot(data=eval_df, x='K', y='Precision@K', hue='Pipeline', palette='Set2', ax=axes[0])\n"
        "    axes[0].set_title('Precision@K Comparison', fontsize=12, fontweight='bold')\n"
        "    axes[0].set_ylabel('Precision@K')\n"
        "    axes[0].set_ylim(0, 0.20)\n\n"
        "    # 2. Recall@K Comparison\n"
        "    sns.barplot(data=eval_df, x='K', y='Recall@K', hue='Pipeline', palette='Set2', ax=axes[1])\n"
        "    axes[1].set_title('Recall@K Comparison', fontsize=12, fontweight='bold')\n"
        "    axes[1].set_ylabel('Recall@K')\n"
        "    axes[1].set_ylim(0, 0.25)\n\n"
        "    # 3. HitRate@K Comparison\n"
        "    sns.barplot(data=eval_df, x='K', y='HitRate@K', hue='Pipeline', palette='Set2', ax=axes[2])\n"
        "    axes[2].set_title('HitRate@K Comparison', fontsize=12, fontweight='bold')\n"
        "    axes[2].set_ylabel('HitRate@K')\n"
        "    axes[2].set_ylim(0, 0.60)\n\n"
        "    plt.tight_layout()\n"
        "    plt.show()\n"
    ),
    nbf.v4.new_markdown_cell("### ML Classification Metrics (Untouched Holdout Test Set)"),
    nbf.v4.new_code_cell(
        "ml_report_path = REPORTS_DIR / 'ml_model_evaluation.md'\n"
        "if ml_report_path.exists():\n"
        "    content = ml_report_path.read_text(encoding='utf-8')\n"
        "    # Print first 60 lines\n"
        "    for line in content.split('\\n')[:60]:\n"
        "        print(line)\n"
        "else:\n"
        "    print('[Not found] reports/ml_model_evaluation.md')\n"
    ),
    nbf.v4.new_markdown_cell(
        "## Key Conclusions & Limitations\n\n"
        "### Key Findings (from `reports/day3_evaluation_results.csv`)\n"
        "| Pipeline | Precision@5 | Recall@5 | HitRate@5 | Policy Compliance |\n"
        "| :--- | :---: | :---: | :---: | :---: |\n"
        "| Popularity Baseline | 0.0464 | 0.0656 | 0.163 | 100% |\n"
        "| Day-3 Recommendation Pipeline | 0.1530 | 0.1921 | 0.489 | 100% |\n\n"
        "### Limitations\n"
        "- Evaluation is conducted on a 300-customer, 52-product synthetic ecosystem. "
        "Real-world scale will require Approximate Nearest Neighbor indexing.\n"
        "- Cold-start customers fall back to popularity baseline.\n"
        "- Association rules and collaborative filtering are not yet implemented "
        "(stubs exist in `backend/app/recommendation/`)."
    ),
]

with open(NB_DIR / "04_recommendation_evaluation.ipynb", "w", encoding="utf-8") as f:
    nbf.write(nb4, f)
print("Created 04_recommendation_evaluation.ipynb")

print("\nAll 4 notebooks populated and updated successfully.")
