# Air Quality Prediction for Indian Cities – Project Report

*IDC409 · Topic 11 · Dataset: `city_day.csv` (CPCB daily city-level air quality, 2015-01-01 → 2020-07-01)*

## Abstract

We built an end-to-end pipeline that stores Indian air-quality data in a SQLite database, cleans and analyses it, reduces its
features, and trains regression and classification models to predict the Air Quality Index (AQI) and its category. Using a strictly
chronological split (train 2015-2018, test 2019 – July 2020), a Random Forest estimates the same-day AQI with MAE 16.0 (R² 0.906)
against 22.4 (R² 0.855) for Linear Regression, and classifies the six CPCB categories with macro-F1 0.756 (baseline 0.608); 99.7 %
of its errors are only one category off. Four of 23 candidate features (PM2.5, PM10, CO, O3) are sufficient. For the harder task of
**forecasting tomorrow's AQI**, ML beats the "tomorrow = today" persistence baseline by ≈ 19 % (MAE 17.1 vs 21.3). We also compare
Delhi, Chandigarh, Mumbai and five nearby / reference cities, quantify the effect of Diwali (+33 AQI points over seasonal drift;
+52 in north India) and of the COVID-19 lockdown (median −31 %), and show that a model that never saw Chandigarh predicts it as
well as one trained on it.

## 1 · Problem and data

The goal is to predict the AQI value (regression) or category (classification) from pollutant concentrations and time features,
and as an extension to compare cities and predict the next day. The dataset has 29,531 daily records for 26 cities with 12
pollutants (PM2.5, PM10, NO, NO2, NOx, NH3, CO, SO2, O3, Benzene, Toluene, Xylene), the AQI and its category. It contains no
weather variables.

Quality problems found and handled:

| Issue | Evidence | Treatment |
|---|---|---|
| Uneven coverage | 6 cities with ≈ 5.5 years; Chandigarh 304 days (Sep 2019 →); Mumbai AQI 61 % missing | like-for-like comparison windows; chronological split |
| Missing values | Xylene 61 %, PM10 38 %, NH3 35 %, Toluene 27 %, Benzene 19 %, PM2.5 / AQI 16 % | Xylene dropped; ≤ 3-day gaps forward-filled per city; the rest imputed inside pipelines (train-only); target never imputed |
| Empty rows | 1,374 rows with all 13 values missing | deleted in SQL |
| Duplicates / names | 0 duplicate (city, date); 26 consistent names | verified and documented |
| Placeholder zeros | e.g. Mumbai ≈ 1,006 identical zero counts in Benzene/Toluene/Xylene | zeros in CO, NOx, Benzene, Toluene, Xylene → NULL |
| Unreliable city | Ahmedabad: mean AQI 452, NO = CO on 85 % of days, 76 % of all AQI > 500 | flagged, excluded from modelling, sensitivity-tested |

## 2 · Database

`sql/schema.sql` defines a raw layer (`raw_city_day`), a dimension (`dim_city`: id, name, state, region), a fact table (`fact_aqi`,
primary key (city_id, date), foreign key to `dim_city`, flags `is_outlier` and `is_suspect`), a festival lookup, an `audit_log`
and a `model_results` table, plus two views. The cleaning pipeline (`sql/clean_pipeline.sql`) is a sequence of named SQL steps
(UPDATE, DELETE, INSERT…SELECT); every step writes its affected-row count to `audit_log`. Fourteen analytical queries exercise
joins, `GROUP BY / HAVING`, `CASE`, window functions and date functions. Notebook 01 also shows an explicit
INSERT → UPDATE → DELETE sequence and a ROLLBACK, and integrity checks (no duplicate keys, no FK violations,
categories consistent with AQI). Result: 28,157 clean rows in `fact_aqi`.

## 3 · Features

Calendar (cyclic month, weekday, weekend, season, winter), events (Diwali window D−1…D+3, Holi and Dussehra windows, the
15 Oct – 30 Nov stubble-burning season, the 25 Mar – 31 May 2020 lockdown) and, for forecasting, lags and rolling statistics of
the AQI and PM. Lags are computed on a gap-free calendar per city. `year` is deliberately not a feature (a tree cannot
extrapolate to unseen years).

A domain check re-implements the CPCB formula (AQI = maximum of pollutant sub-indices). It reproduces the dataset's AQI with
R² 0.87 and shows that PM2.5 or PM10 sets the AQI on most days. Consequence: same-day regression is largely "learning the formula";
the genuinely predictive task is next-day forecasting.

## 4 · Exploratory findings

* **Cities:** Delhi mean AQI 260 (65 % of days Poor or worse), Patna 241, Gurugram 225; cleanest Coimbatore 73, Thiruvananthapuram 76,
  Bengaluru 94. Regions: North 200, East 184, others 100–133.
* **Seasonality:** north Indian cities peak in November at ≈ 3× their trough, southern ones vary only ≈ 1.6×. Winter 204,
  post-monsoon 191, summer 135, monsoon 100.
* **Weekday effect:** negligible (largest swing ≈ 4.6 points).
* **Pollutants:** PM10 and PM2.5 correlate most with AQI (Spearman 0.88); PM2.5 dominates in Delhi, Gurugram, Lucknow; PM10 in
  Chandigarh, Amritsar, Jaipur, Mumbai.
* **Festivals (placebo-controlled):** Diwali +37.8 % vs +4.8 % for placebo dates (excess ≈ +33 points; north India +46 % vs −6 %);
  Holi no excess; Dussehra +37 % vs +11 % but confounded with the autumn onset. Stubble season: +125 % in north India vs +94 % elsewhere.
* **Lockdown:** median −31 % AQI over 18 cities; PM10 −40 %, PM2.5 −37 %, NO2 −36 %, CO −27 %, SO2 −17 %, O3 ≈ 0.

## 5 · Feature reduction

Methods: Spearman and mutual information, VIF, greedy correlation filter, permutation and impurity importance, PCA. All selection
used the training period only; the final choice used 4-fold expanding-window time-series CV.

| Feature set (Gradient Boosting) | Features | Test R² | Test MAE |
|---|---|---|---|
| Full | 23 | 0.908 | 16.5 |
| **Importance, CV-selected** | **4 (PM2.5, PM10, CO, O3)** | **0.905** | **16.2** |
| Correlation filter | 21 | 0.874 | 19.1 |
| PCA (95 % variance) | 22 | 0.823 | 21.0 |
| Importance, naive single-year pick | 2 | 0.883 | 19.5 |

VIFs are all < 3.4 (no severe multicollinearity). The correlation filter hurts because it drops PM10 (ρ = 0.81 with PM2.5) although
the AQI is a maximum over pollutants and PM10 carries unique information. Calendar and festival features have ≈ 0 importance for
same-day prediction because their effect is already contained in the pollutant readings.

## 6 · Same-day prediction

**Regression** (test MAE / RMSE / R²): Mean 82.9 / 95.1 / −0.29 · **Linear Regression 22.4 / 31.9 / 0.855** · Decision Tree 17.9 / 28.1 /
0.887 · Random Forest 15.96 / 25.7 / 0.906 · Gradient Boosting 16.05 / 25.4 / 0.908 · Neural Net 16.3 / 24.7 / 0.913 · CPCB
formula without ML 18.4 / 27.9 / 0.889. Hyper-parameters were tuned with randomized search and 3-fold time-series CV on MAE. The
ML models beat the official formula because they learn the dataset's own calibration. Errors rise with AQI level (Linear Regression
MAE ≈ 18 below AQI 100, ≈ 95 above 400; non-linear models roughly halve the high-end error). Per-city MAE ranges from 7 (Bengaluru)
to 25 (Guwahati); Chandigarh, never seen in training, gets 14.8. Including Ahmedabad in training changes nothing for the other
cities (R² identical to 3 decimals) and the model cannot predict Ahmedabad itself (R² ≈ 0.73). A shuffled-target control scores
R² = −0.28.

**Classification** (six classes; macro-F1 / accuracy): Majority 0.087 / 0.353 · **Logistic Regression 0.608 / 0.602** · Decision Tree
0.703 / 0.726 · Gradient Boosting 0.733 / 0.761 · Neural Net 0.746 / 0.785 · **Random Forest 0.756 / 0.785**. Errors are almost
always adjacent classes (78.5 % exact, 21.2 % off by one, 0.3 % by two). Class weights raise the recall of *Good* from 0.55 to 0.78.
Direct classification beats "regress then bucket" on balanced accuracy (0.77 vs ≤ 0.71). Mumbai is the hardest city (66.6 %
accuracy) because its AQI hovers around the 100 boundary. A shuffled-label control gives macro-F1 0.12.

## 7 · Extension: city comparison and next-day forecast

**Comparison (2 Sep 2019 – 1 Jul 2020).** Mean AQI: Delhi 216 (45 % bad days), Gurugram 186, Lucknow 185, Jaipur 114, Amritsar 112,
Mumbai 110, **Chandigarh 97 (7.7 %)**, Bengaluru 81. Daily AQI correlation: Delhi–Gurugram 0.96, Delhi–Chandigarh 0.79,
Chandigarh–Amritsar 0.73, Chandigarh–Mumbai 0.30; correlations peak at lag 0. Diwali 2019: Amritsar +140 %, Chandigarh +124 %, Jaipur
+72 %, Delhi +59 %, Gurugram +46 %, Mumbai −3 %. A pooled model beats city-specific models (Chandigarh MAE 9.1 vs 14.5), and a
zero-shot pooled model works as well (8.95).

**Next-day forecast** (rows whose target date lies in the test period are excluded from training; tomorrow's calendar flags
allowed, as festivals are known in advance). Persistence: MAE 21.3, R² 0.802. Random Forest 17.1 / 0.887 (−19.5 %), Gradient Boosting
17.3 / 0.889, Linear Regression 18.9 / 0.873, Decision Tree 19.3 / 0.870, Neural Net 21.7 / 0.851 (no gain). An ablation shows AQI
history alone does not beat persistence (MAE 21.5–22.4) while adding today's pollutant readings gives MAE 17.2–18.5, because the AQI
is a maximum that discards information. Festival flags add little overall (17.64 → 17.52) but reduce the north-India Diwali-day
error from 43.3 to 40.5 (persistence 53.5; n = 30). Next-day category: Random Forest accuracy 0.774, macro-F1 0.746 vs persistence 0.737 / 0.676;
Logistic Regression and Decision Tree fall below persistence.

## 8 · Discussion and limitations

The strongest scientific lessons are methodological: (i) a random split would have inflated every number, (ii) a high same-day R² is
expected because AQI is computed from the inputs, so a baseline that encodes this (the CPCB formula, persistence) is needed to judge
"skill", (iii) single-year validation chose a worse feature set than time-series CV, (iv) festival effects must be measured against
seasonal drift. Limitations: no weather data; Chandigarh has ten months and Mumbai mostly missing AQI; the test period contains the
lockdown; festival dates are hard-coded; only one-day horizons; no prediction intervals.

## 9 · Conclusion

Particulate readings (PM2.5, PM10) plus CO and O3 are enough to estimate the AQI of any Indian city with an average error of about
16 points and to classify its category with ≈ 79 % accuracy and almost no multi-class errors; tree ensembles and a small neural net
clearly beat linear baselines. Forecasting tomorrow is genuinely harder: persistence is strong, and ML improves on it by about a
fifth, mainly through the information in individual pollutant readings. Chandigarh's air is about as good as Mumbai's and more than
twice as clean as Delhi's, but it reacts sharply to Diwali. Meteorological data are the natural next step.

## References
* Central Pollution Control Board (India), *National Air Quality Index* – sub-index breakpoints and methodology.
* Kaggle / CPCB, *Air Quality Data in India (2015-2020)* – source of `city_day.csv`.
* Pedregosa et al., *Scikit-learn: Machine Learning in Python*, JMLR 12, 2011.
