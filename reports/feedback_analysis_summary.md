# Mutual Fund SIP Retention & Churn: Discovery Engine Analysis Summary

## 1. Scope & Analyzed Volume by Source

| Data Source | Raw Rows | Excluded Rows | Analyzed Rows | Notes |
| :--- | :---: | :---: | :---: | :--- |
| **Google Forms Survey** | 32 | 8 | **24** | Excluded 8 non-investors (`Q1 == 'No'`) to focus on investor retention |
| **Google Play Reviews (Batch 1)** | 530 | 424 | **106** | 424 pagination duplicates removed; 106 unique reviews |
| **Google Play Reviews (Batch 2)** | 100 | 80 | **20** | 80 pagination duplicates removed; 20 unique reviews |
| **Reddit Groww Concerns** | 56 | 3 | **53** | Excluded 3 `[deleted]` comments; preserved thread integrity |
| **Total Mutual Fund & Platform** | **718** | **515** | **203** | **Core discovery dataset for Mutual Fund SIP retention** |

### Isolated Stock SIP Discussions (Strictly Segregated)

* **Reddit Stock SIP Thread:** **7 comments** analyzed in a separate domain. These discussions address single-equity systematic investing and are **excluded** from mutual fund retention findings.

## 2. Identified Themes & Distribution

| Theme | Count | % of MF Feedback | Core Driver Type |
| :--- | :---: | :---: | :--- |
| **Uncertain / Ambiguous Feedback** | **63** | 31.0% | Needs Clarification |
| **Customer Support & Service Friction** | **34** | 16.7% | Churn / Pause Driver |
| **Platform Trust, Technical Friction & Mandate Failures** | **28** | 13.8% | Churn / Pause Driver |
| **Platform Usability, UI Speed & Design Ease** | **23** | 11.3% | Retention Enabler |
| **Deliberate Pausing, Stopping & Alternative Migration** | **19** | 9.4% | Churn / Pause Driver |
| **Investment Literacy & Understanding Gaps** | **12** | 5.9% | Churn / Pause Driver |
| **Financial Constraints & Cash-Flow Liquidity** | **10** | 4.9% | Churn / Pause Driver |
| **Market Volatility Anxiety & Uncertainty** | **7** | 3.4% | Churn / Pause Driver |
| **SIP Continuation & Goal Enablers** | **7** | 3.4% | Retention Enabler |

## 3. Representative Supporting Comments by Theme

### Uncertain / Ambiguous Feedback (63 records)

- **[google_play_b1 - GROWW_REV_B1_006]**: *"ridiculous new update. When we open the charts the back button on our phone just disappears and we end up clicking the scalper mode or a different chart when not needed. Also the limit order is auto f..."*
  - **Evidence:** `Off-topic F&O or derivatives trading feedback.`
  - **Confidence:** `uncertain`

- **[google_play_b1 - GROWW_REV_B1_009]**: *"The app is super buggy at times, with painstakingly slow loading times for the market data, and this sometimes happen during the peak trading hours. When you reach out to support they keep saying same..."*
  - **Evidence:** `No domain-specific SIP or platform keywords detected.`
  - **Confidence:** `uncertain`

### Customer Support & Service Friction (34 records)

- **[google_play_b1 - GROWW_REV_B1_002]**: *"Extremely frustrated with Groww. First, my stop-loss order got triggered incorrectly at a higher price (₹148.18) when the actual market price was at ₹146.90, causing me a direct financial loss. Second..."*
  - **Evidence:** `Matched keywords: [pathetic service, support]`
  - **Confidence:** `high`

- **[google_play_b1 - GROWW_REV_B1_005]**: *"I have been a groww customer for the last 5 years. Since last month I have been trying to update my e-mail id but due to reasons unknown it has failed number of times. Everytime I tried changing the e..."*
  - **Evidence:** `Matched keywords: [care, mail id but due to reasons unknown it has failed number of times. everytime i tried changing the email id it shows "account creation is in process.plz try again once the account is activated''. i contacted the customer care number of times but they failed to resolve the issue. also the customer support, support]`
  - **Confidence:** `high`

- **[google_play_b1 - GROWW_REV_B1_011]**: *"worst support team ever guys please don't use this application it's so frustrating to talk with the support team when you'll be explaining something they'll leave your call on hold i experienced it wh..."*
  - **Evidence:** `Matched keywords: [support team, no response]`
  - **Confidence:** `high`

### Platform Trust, Technical Friction & Mandate Failures (28 records)

- **[google_play_b1 - GROWW_REV_B1_001]**: *"Your app gets stuck far too often at the time of trade execution, and even after setting a profit/loss limit, the order does not get executed automatically. I have incurred losses so many times becaus..."*
  - **Evidence:** `Matched keywords: [app gets stuck, stuck]`
  - **Confidence:** `high`

- **[google_play_b1 - GROWW_REV_B1_003]**: *"My bank account has been blocked due to an unexpected transaction from Groww. I did not initiate or withdraw any money, yet funds were automatically credited to my account. It has been almost a month,..."*
  - **Evidence:** `Matched keywords: [blocked, bank account]`
  - **Confidence:** `high`

- **[google_play_b1 - GROWW_REV_B1_007]**: *"poor services, order placing gets stuck. many times loss booked due to platform inconvenience. even customer support works poorly. & now also they will write back like to send feedback on email. then ..."*
  - **Evidence:** `Matched keywords: [stuck, order placing gets stuck]`
  - **Confidence:** `high`

### Platform Usability, UI Speed & Design Ease (23 records)

- **[google_play_b1 - GROWW_REV_B1_004]**: *"Groww is very easy to use compared to many apps, which I really like. However, there is no separate category or dedicated section for International Mutual Funds, making it difficult to find all availa..."*
  - **Evidence:** `Matched keywords: [use]`
  - **Confidence:** `high`

- **[google_play_b1 - GROWW_REV_B1_016]**: *"Worst for trading or chart reading. Use this only for SIPs. It literally gave me an alert saying that the stock had reached my target, but when I checked the chart on my PC, the price was still 100 po..."*
  - **Evidence:** `Matched keywords: [chart]`
  - **Confidence:** `high`

- **[google_play_b1 - GROWW_REV_B1_019]**: *"The current update made it worst experience. the indicators are not upto the mark, the back button drawer hides constantly, which results in selecting unwanted options. previous version was way better..."*
  - **Evidence:** `Matched keywords: [update]`
  - **Confidence:** `high`

### Deliberate Pausing, Stopping & Alternative Migration (19 records)

- **[google_forms - FORM_RESP_001]**: *"Status: Stopped | Tenure: 12–24 months | Confusing aspects: 'Understanding market ups and downs, Knowing whether I chose the right amount, Understanding charges or taxes' | Pause/Stop reasons: 'None' ..."*
  - **Evidence:** `Status: Stopped`
  - **Confidence:** `high`

- **[google_forms - FORM_RESP_011]**: *"Status: Stopped | Tenure: 12–24 months | Confusing aspects: 'Understanding market ups and downs' | Pause/Stop reasons: 'Lost interest' | Continuation factors: 'Educational content, Better understandin..."*
  - **Evidence:** `Selected: Lost interest`
  - **Confidence:** `high`

- **[google_play_b1 - GROWW_REV_B1_091]**: *"i am trading in Groww for almost 6months. They are charging more as order fee. For big investment(more than 50000) its not a problem. I usually trade for 5000 to 10000 my profit most of the time goes ..."*
  - **Evidence:** `Matched keywords: [stopped]`
  - **Confidence:** `high`

### Investment Literacy & Understanding Gaps (12 records)

- **[google_forms - FORM_RESP_030]**: *"Status: Paused | Tenure: 3–6 months | Confusing aspects: 'Knowing whether I chose the right amount' | Pause/Stop reasons: 'Found another investment option, Did not understand what was happening' | Con..."*
  - **Evidence:** `Selected: Did not understand what was happening`
  - **Confidence:** `high`

- **[google_play_b1 - GROWW_REV_B1_014]**: *"Very disappointing experience with Groww. The charges are too high compared to other investment apps, especially when selling stocks. The deductions are not always easy to understand, and the overall ..."*
  - **Evidence:** `Matched keywords: [s, charges]`
  - **Confidence:** `high`

- **[google_play_b1 - GROWW_REV_B1_015]**: *"Very Disappointing Experience with Groww I bought shares for ₹200 and held them for 5–6 days. When the share price reached ₹220, I sold them expecting to receive my profit. However, after the transact..."*
  - **Evidence:** `Matched keywords: [s, charges]`
  - **Confidence:** `high`

### Financial Constraints & Cash-Flow Liquidity (10 records)

- **[google_forms - FORM_RESP_003]**: *"Status: Paused | Tenure: Less than 3 months | Confusing aspects: 'Knowing whether I chose the right amount, Understanding whether my investment is doing well, Understanding charges or taxes' | Pause/S..."*
  - **Evidence:** `Selected: App experience issues, Job change or uncertainty`
  - **Confidence:** `high`

- **[google_forms - FORM_RESP_007]**: *"Status: Reduced the amount | Tenure: Less than 3 months | Confusing aspects: 'Understanding market ups and downs, Understanding whether my investment is doing well' | Pause/Stop reasons: 'Job change o..."*
  - **Evidence:** `Selected: Job change or uncertainty`
  - **Confidence:** `high`

- **[google_forms - FORM_RESP_009]**: *"Status: Paused | Tenure: 6–12 months | Confusing aspects: 'Nothing was confusing, Understanding where my money is invested, Understanding whether my investment is doing well' | Pause/Stop reasons: 'Lo..."*
  - **Evidence:** `Selected: Lower income or cash-flow pressure, Job change or uncertainty`
  - **Confidence:** `high`

### Market Volatility Anxiety & Uncertainty (7 records)

- **[google_forms - FORM_RESP_004]**: *"Status: Paused | Tenure: 6–12 months | Confusing aspects: 'Understanding where my money is invested' | Pause/Stop reasons: 'Market fall or negative returns, Found another investment option, App experi..."*
  - **Evidence:** `Selected: Market fall or negative returns`
  - **Confidence:** `high`

- **[google_forms - FORM_RESP_008]**: *"Status: Stopped | Tenure: 6–12 months | Confusing aspects: 'Understanding whether my investment is doing well, Knowing whether I chose the right amount, Nothing was confusing' | Pause/Stop reasons: 'D..."*
  - **Evidence:** `Selected: Market fall or negative returns`
  - **Confidence:** `high`

- **[google_forms - FORM_RESP_012]**: *"Status: Stopped | Tenure: 6–12 months | Confusing aspects: 'Understanding market ups and downs, Knowing whether I chose the right amount' | Pause/Stop reasons: 'Market fall or negative returns, Found ..."*
  - **Evidence:** `Selected: Market fall or negative returns`
  - **Confidence:** `high`

### SIP Continuation & Goal Enablers (7 records)

- **[google_forms - FORM_RESP_006]**: *"Status: Active | Tenure: 6–12 months | Confusing aspects: 'Understanding where my money is invested' | Pause/Stop reasons: 'Lower income or cash-flow pressure, Market fall or negative returns' | Conti..."*
  - **Evidence:** `Active SIP investor; Continuation factors: Educational content, Flexible pause or reduce options`
  - **Confidence:** `high`

- **[google_forms - FORM_RESP_010]**: *"Status: Active | Tenure: 12–24 months | Confusing aspects: 'Understanding where my money is invested, Understanding whether my investment is doing well, Understanding charges or taxes' | Pause/Stop re..."*
  - **Evidence:** `Active SIP investor; Continuation factors: Educational content, Better understanding of where my money goes`
  - **Confidence:** `high`

- **[google_forms - FORM_RESP_021]**: *"Status: Active | Tenure: 12–24 months | Confusing aspects: 'Understanding charges or taxes' | Pause/Stop reasons: 'App experience issues, Did not understand what was happening' | Continuation factors:..."*
  - **Evidence:** `Active SIP investor; Continuation factors: Clear explanation of short-term ups and downs`
  - **Confidence:** `high`

## 4. Key Limitations & Uncertain Findings

1. **Self-Reported Intent vs. Actual 12-Month Bank Telemetry:** Survey responses represent respondents' stated perceptions and attitudes. They do not substitute for longitudinal transactional records of 12-month auto-debit success rates.
2. **Negativity Skew in App Store Reviews:** Review platforms over-represent dissatisfied users who experienced transaction failures, KYC delays, or account blocks. Satisfied SIP investors rarely post reviews unless prompted.
3. **Stock SIP vs Mutual Fund SIP Segregation:** Single-equity SIPs involve company-specific stock market volatility and trading charges; they have been kept separate to avoid distorting mutual fund findings.
4. **Ambiguous Feedback Records:** 63 records were classified as uncertain because they referenced F&O option trading, generic one-word praise, or lacked clear mutual fund context.
5. **Exploratory Survey Sample:** The 24 active survey respondents provide qualitative direction for product discovery, but quantitative generalizations should be verified against larger production cohorts.
