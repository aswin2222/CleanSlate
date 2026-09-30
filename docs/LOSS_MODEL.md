# CleanSlate - Information Loss Modeling & Quantification
Document Version: 1.0.0
Compliance: Section 4.6 / Requirement R3

---

## 1. Mathematical Formulation

Prior to applying any transformation pipeline to an enterprise dataset, CleanSlate executes a deterministic `dry_run` against an in-memory scratch projection. Information loss is formulated as a normalized composite score $S \in [0, 100]$:

$$S = 100 \times \left(0.35 \cdot C_{\text{row}} + 0.15 \cdot C_{\text{cell}} + 0.20 \cdot C_{\text{dist}} + 0.15 \cdot C_{\text{entropy}} + 0.10 \cdot C_{\text{card}} + 0.05 \cdot C_{\text{corr}}\right)$$

### 1.1 Loss Components

1. **Row Deletion Component ($C_{\text{row}}$)**
   Measures the fraction of total records purged (e.g., via deduplication or rule rejection):
   $$C_{\text{row}} = \min\left(1.0, \frac{\text{rows\_removed}}{\text{total\_rows} \times 0.10}\right)$$
   *Rationale*: Eliminating rows destroys entire sample records. Purging more than 10% of rows maximizes this component penalty to 1.0.

2. **Cell Mutation Component ($C_{\text{cell}}$)**
   Quantifies the proportion of all cell coordinates $(r, c)$ modified:
   $$C_{\text{cell}} = \min\left(1.0, \frac{\text{cells\_modified}}{\text{total\_cells} \times 0.25}\right)$$
   *Rationale*: Broad alterations across multiple columns degrade raw evidentiary value.

3. **Distribution Shift ($C_{\text{dist}}$)**
   Evaluates statistical divergence across affected columns:
   - For **categorical columns**, Jensen-Shannon Divergence (base 2, $JSD \in [0, 1]$):
     $$JSD(P \parallel Q) = \frac{1}{2} D_{KL}(P \parallel M) + \frac{1}{2} D_{KL}(Q \parallel M), \quad M = \frac{1}{2}(P + Q)$$
   - For **numeric columns**, normalized 1D Wasserstein distance (earth mover's distance):
     $$W_1(u, v) = \int_{-\infty}^\infty |U(x) - V(x)| dx, \quad C_{\text{numeric}} = \min\left(1.0, \frac{W_1(u, v)}{\max(10^{-6}, P_{95} - P_{5})}\right)$$
   $C_{\text{dist}}$ is the arithmetic mean across all affected columns.

4. **Shannon Entropy Change ($C_{\text{entropy}}$)**
   Measures information content and diversity loss across column value distributions:
   $$H(X) = - \sum_{x \in \mathcal{X}} p(x) \log_2 p(x)$$
   $$C_{\text{entropy}} = \frac{1}{|\mathcal{A}|} \sum_{c \in \mathcal{A}} \min\left(1.0, \left|\frac{H_{\text{after}}(c) - H_{\text{before}}(c)}{\max(10^{-6}, H_{\text{before}}(c))}\right|\right)$$

5. **Cardinality Reduction ($C_{\text{card}}$)**
   Tracks the destruction of unique distinct values:
   $$C_{\text{card}} = \frac{1}{|\mathcal{A}|} \sum_{c \in \mathcal{A}} \min\left(1.0, \frac{|\mathcal{U}_{\text{before}}(c)| - |\mathcal{U}_{\text{after}}(c)|}{\max(1, |\mathcal{U}_{\text{before}}(c)|)}\right)$$

6. **Correlation Drift ($C_{\text{corr}}$)**
   Measures the perturbation of inter-feature Pearson correlation among numeric pairs:
   $$C_{\text{corr}} = \min\left(1.0, \frac{1}{\binom{|\mathcal{N}|}{2}} \sum_{i < j} |\rho_{\text{after}}(i, j) - \rho_{\text{before}}(i, j)|\right)$$
   (Defaults to 0 if fewer than 2 numeric columns exist).

---

## 2. Risk Classification & Labels

The computed score $S$ maps to discrete human-governed safety bands:

| Loss Score Range | Label | Policy & Behavior |
|---|---|---|
| **$0 \le S < 20$** | **LOW** | Safe routine transformation (e.g. whitespace trimming, missing marker normalization, standard date parsing). Approved by default. |
| **$20 \le S \le 50$** | **MEDIUM** | Moderate distortion (e.g. category consolidation, median imputation). Flagged for review; highlights affected histograms. |
| **$S > 50$** | **HIGH** | Severe information loss (e.g. aggressive row dropping, radical winsorizing). **Hard approval gate**: execution blocked until human explicit override. |

---

## 3. Human-Readable Explanation Generation

CleanSlate produces an automated impact sentence summarizing concrete changes:
> *"Drops 312 rows (3.1%), destroys 4,368 non-null cells, shifts 'total_amount' mean by +0.2%. Loss: LOW (12.4/100)."*

## 4. Calibration & Verification Guarantee
- On datasets up to 500,000 rows, dry-run calculations are 100% exact.
- Count-based metrics (`rows_removed`, `cells_modified`) have an error tolerance of exactly 0.00%.
- For datasets $> 500,000$ rows evaluated via stratified sampling, a 95% confidence interval is published, and actual post-execution loss is calibrated and compared.
