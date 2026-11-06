# Classifier Evaluation & Disagreement Report

## 1. Executive Summary & Comparative Metrics

Primary Benchmark Set: **25 curated records** ([benchmark_samples.csv](file:///C:/Users/fathi/Desktop/Project/data/evaluation/benchmark_samples.csv))
Independent Holdout Set: **20 unseen records** ([holdout_samples.csv](file:///C:/Users/fathi/Desktop/Project/data/evaluation/holdout_samples.csv))
Active LLM Provider Evaluated: **MockLLMClient**

> [!NOTE]
> **Mock LLM vs. Real LLM Performance Separation**:
> The LLM metrics shown below reflect the offline deterministic `MockLLMClient` test double, which executes local heuristic pattern matching to validate pipeline plumbing, fallback paths, and CI/CD tests without making paid external API calls. Mock LLM performance figures should NOT be conflated with real production LLM accuracy (e.g., Google Gemini 1.5/2.0 or OpenAI GPT-4o), which leverage extensive contextual semantics and few-shot reasoning beyond local rule sets.

> [!IMPORTANT]
> **Preliminary Nature of 100% Benchmark Accuracy**:
> The 100.0% accuracy on the 25-sample benchmark is a **preliminary in-sample figure**. Rule heuristics were iteratively refined against these exact 25 benchmark instances (data leakage). When evaluated against an independent, unseen 20-sample holdout dataset, the rule-based classifier achieved **90.0%**, and the Mock LLM achieved **55.0%**. True production accuracy must NOT be claimed as 100%.

| Evaluation Set | Total Samples | Rule-Based Accuracy | Mock LLM (Offline Baseline) | Inter-Classifier Agreement | Notes |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Tuned Benchmark** | 25 | **100.0%** (25/25) | **80.0%** (20/25) | **80.0%** (20/25) | Preliminary in-sample tuning set |
| **Independent Holdout** | 20 | **90.0%** (18/20) | **55.0%** (11/20) | **65.0%** (13/20) | Unseen real reviews & survey records |

## 2. Disagreement & Edge Case Analysis

### A. Benchmark Disagreements (5 Records Detailed Root Causes)

| Record ID | Feedback Excerpt | Rule Prediction | Mock LLM Prediction | Expected Ground Truth | Root Cause Analysis |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `BENCH_005` | *"I cannot understand what are the exit load charges and why 2..."* | **Investment Literacy & Understanding Gaps** | **Platform Trust, Technical Friction & Mandate Failures** | `Investment Literacy & Understanding Gaps` | Mock LLM matches 'deducted' in rule #3 (Platform Trust) before checking exit load/charges in rule #6 (Investment Literacy). |
| `BENCH_007` | *"Status: Active | Tenure: 12–24 months | Continuation factors..."* | **SIP Continuation & Goal Enablers** | **Investment Literacy & Understanding Gaps** | `SIP Continuation & Goal Enablers` | Mock LLM matches substring 'understand' inside 'understanding' in rule #6 before evaluating active continuation factors in rule #8. |
| `BENCH_016` | *"Stopped my monthly SIP on Groww and shifted my portfolio to ..."* | **Deliberate Pausing, Stopping & Alternative Migration** | **Platform Trust, Technical Friction & Mandate Failures** | `Deliberate Pausing, Stopping & Alternative Migration` | Mock LLM matches 'mandate' in 'Coin direct AMC mandate' in rule #3 before recognizing competitor churn ('shifted/stopped') in rule #7. |
| `BENCH_018` | *"The new chart update is very confusing and the back button k..."* | **Platform Usability, UI Speed & Design Ease** | **Investment Literacy & Understanding Gaps** | `Platform Usability, UI Speed & Design Ease` | Mock LLM matches 'confusing' in rule #6 (Investment Literacy) rather than UI design/chart layout usability. |
| `BENCH_021` | *"Is it safe to keep large sums in Groww? What happens if Grow..."* | **Investment Literacy & Understanding Gaps** | **Market Volatility Anxiety & Uncertainty** | `Investment Literacy & Understanding Gaps` | Mock LLM matches substring 'down' inside 'shuts down' in rule #4 (Market Volatility) before custody/pool account checks in rule #6. |

### B. Holdout Unseen Errors & Boundary Cases (Rule-Based Classifier)

| Record ID | Source | Feedback Excerpt | Rule Prediction | Expected Label | Limitation / Edge Case |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `HOLDOUT_002` | `google_play` | *"Unable to log in for the last few days. It keeps showing: Your jo..."* | **Uncertain / Ambiguous Feedback** | `Platform Trust, Technical Friction & Mandate Failures` | Novel phrasing for account lock ('journey reset') lacked explicit login/stuck keywords. |
| `HOLDOUT_009` | `google_play` | *"Very good experience so far with Groww mutual fund...."* | **Uncertain / Ambiguous Feedback** | `SIP Continuation & Goal Enablers` | General positive sentiment ('good experience') lacked active SIP continuation verbs. |

## 3. Detailed Evidence Extraction Samples

### Record `BENCH_001` (google_play)
- **Feedback:** *"Customer care never picks up call, ticket closed without resolving my issue."*
- **Expected Theme:** `Customer Support & Service Friction`
- **Rule Classifier:** `Customer Support & Service Friction` (Confidence: `high`, Evidence: `Matched keywords: [care, ticket]`)
- **LLM Classifier:** `Customer Support & Service Friction` (Confidence: `high`, Evidence: `LLM evidence: 'customer care / support' (extracted snippet)`)
- **Status:** ✅ Exact Match

### Record `BENCH_002` (google_play)
- **Feedback:** *"My auto-debit failed 3 times this month, bank mandate says approved but Groww says payment delayed."*
- **Expected Theme:** `Platform Trust, Technical Friction & Mandate Failures`
- **Rule Classifier:** `Platform Trust, Technical Friction & Mandate Failures` (Confidence: `high`, Evidence: `Matched keywords: [payment delayed, auto-debit, failed, mandate, delayed]`)
- **LLM Classifier:** `Platform Trust, Technical Friction & Mandate Failures` (Confidence: `high`, Evidence: `LLM evidence: 'mandate / payment / technical failure' (extracted snippet)`)
- **Status:** ✅ Exact Match

### Record `BENCH_003` (google_forms)
- **Feedback:** *"Status: Paused | Tenure: 6–12 months | Pause/Stop reasons: 'Market fall or negative returns' | Confusing aspects: 'Understanding market ups and downs'"*
- **Expected Theme:** `Market Volatility Anxiety & Uncertainty`
- **Rule Classifier:** `Market Volatility Anxiety & Uncertainty` (Confidence: `high`, Evidence: `Matched keywords: [ups and downs, negative returns, market fall]`)
- **LLM Classifier:** `Market Volatility Anxiety & Uncertainty` (Confidence: `high`, Evidence: `market fall or negative returns`)
- **Status:** ✅ Exact Match

### Record `BENCH_004` (google_forms)
- **Feedback:** *"Status: Reduced the amount | Tenure: Less than 3 months | Pause/Stop reasons: 'Job change or uncertainty, Lower income or cash-flow pressure'"*
- **Expected Theme:** `Financial Constraints & Cash-Flow Liquidity`
- **Rule Classifier:** `Financial Constraints & Cash-Flow Liquidity` (Confidence: `high`, Evidence: `Matched keywords: [change, cash-flow, income, lower income]`)
- **LLM Classifier:** `Financial Constraints & Cash-Flow Liquidity` (Confidence: `high`, Evidence: `LLM evidence: 'job change / income pressure' (extracted snippet)`)
- **Status:** ✅ Exact Match

### Record `BENCH_005` (google_play)
- **Feedback:** *"I cannot understand what are the exit load charges and why 20 rupees was deducted on redemption."*
- **Expected Theme:** `Investment Literacy & Understanding Gaps`
- **Rule Classifier:** `Investment Literacy & Understanding Gaps` (Confidence: `high`, Evidence: `Matched keywords: [cannot, redemption, charges, deducted]`)
- **LLM Classifier:** `Platform Trust, Technical Friction & Mandate Failures` (Confidence: `high`, Evidence: `LLM evidence: 'mandate / payment / technical failure' (extracted snippet)`)
- **Status:** ⚠️ Disagreement

## 4. Key Takeaways for Product Management
1. **In-Sample Benchmark vs Holdout Reality:** The 100% rule-based accuracy on the initial 25 benchmark records reflected rule development on that specific sample set. On an independent, unseen 20-sample holdout dataset, accuracy was **90.0%**, demonstrating good generalization but proving that 100% production accuracy is an overstatement.
2. **Mock LLM Limitations:** The offline `MockLLMClient` exhibits brittle waterfall regex heuristics (55% on holdout). Its performance must never be used to assess real LLM model capability.
3. **Taxonomy & Multi-Label Gaps:** Real investor feedback frequently spans multiple drivers simultaneously (e.g. emergency cash crunch combined with technical skip failures). Current single-label assignment discards valid secondary drivers.
4. **Missing Regulatory & KYC Themes:** Centralized CAMS/KFintech KYC verification and bank mandate rejection re-KYC requirements currently lack a distinct thematic bucket, forcing them into general platform technical friction.
5. **Strategic Recommendation:** Before building an investor-facing retention feature, the team should validate multi-label classification on a larger holdout sample (100+ items) or calibrate real Gemini API prompt evaluations.
