# Viva / presentation cheat-sheet – questions you will probably get

Short, honest answers backed by what is actually in the repository. Notebook numbers in brackets.

## Data and database

**1. Why use a database at all if the data is one CSV?**
The course asks for read / write / modify. We keep the raw data untouched (`raw_city_day`), do cleaning as logged SQL steps
(`audit_log` records every UPDATE / DELETE), separate city attributes into a dimension table, and store features and model results
back into the database. That gives reproducibility and traceability (nb 01).

**2. Which SQL operations did you use?**
CREATE TABLE / INDEX / VIEW; INSERT (bulk + `INSERT…SELECT`); SELECT with JOIN, GROUP BY, HAVING, CASE, window function
(`AVG() OVER`), date functions; UPDATE (zeros→NULL, flags, city metadata); DELETE (duplicates, empty rows); a transaction with ROLLBACK.

**3. What cleaning did you do and why?**
0 duplicates and 26 consistent city names (verified); 1,374 completely empty rows deleted; placeholder zeros in CO / NOx / Benzene /
Toluene / Xylene set to NULL (Mumbai has ≈ 1,006 identical zero counts → "no reading" encoded as 0); Ahmedabad flagged as unreliable.

**4. Why is Ahmedabad excluded?**
Mean AQI 452 (2–4× others), NO equals CO on ≈ 85 % of days (copy-paste signature), 76 % of all AQI > 500. We keep it in the
database but flag it; notebook 05 shows that including it changes nothing for other cities and that no model can predict it well.

**5. Why six classes when the slide lists five?**
The CPCB scale (and the data) has Good, **Satisfactory**, Moderate, Poor, Very Poor, Severe. Dropping Satisfactory would mislabel 35 % of days.

## Features and EDA

**6. What is the AQI and how is it computed?**
Per pollutant a sub-index is interpolated from CPCB breakpoints; the AQI is the **maximum** sub-index (≥ 3 pollutants, one of them PM).
We re-implemented it (`src/cpcb.py`); it reproduces the dataset's AQI with R² ≈ 0.87 (nb 02).

**7. Doesn't that make your regression trivial?**
Partly – we say so. Same-day AQI is almost a function of the inputs, so we (a) report the CPCB formula itself as a no-ML reference
(MAE 18.4; our ML models get 16.0), and (b) treat **next-day forecasting** as the real prediction task with a persistence baseline.

**8. How did you treat missing values?**
Xylene (61 %) dropped; gaps ≤ 3 days forward-filled within a city (causal); remaining NaNs are handled inside the model pipeline: trees use
native NaN support, linear / NN models use median imputation fitted on the training data. The target is never imputed. We compared
median with MICE – equal accuracy, so we kept the simpler one (nb 02).

**9. What festival effects did you find, and how do you know they are not just seasonality?**
We compare each festival window with the week before **and** repeat the same test on placebo dates ±30 days. Diwali: +37.8 % vs +4.8 %
placebo → ≈ +33 points; north India +46 % vs −6 %. Holi: nothing. Dussehra looks significant but coincides with the autumn onset, so we call it an upper bound (nb 03).

**10. Is the festival calendar reliable?**
Dates are hard-coded in `src/config.py` for 2015-2020 (Diwali, Holi, Dussehra). They should be checked against an official calendar; this is stated as a limitation.

**11. What did the COVID lockdown do?**
Median −31 % AQI over 18 cities versus the same dates in 2019 (Delhi −44 %, Mumbai −27 %); PM10 −40 %, NO2 −36 %, ozone ≈ 0 (nb 03).

## Modelling and evaluation

**12. Why a chronological split instead of a random one?**
Air quality is autocorrelated; a random split puts neighbouring days in train and test and inflates scores. We train on 2015-2018 and test on 2019 – July 2020, tune with `TimeSeriesSplit`.

**13. How do you know there is no data leakage?**
Imputers / scalers / PCA are fitted inside pipelines on training data; `AQI` is never a feature for classification (asserted in code); next-day training rows whose target date is in the test period are removed;
shuffled-target controls give R² = −0.28 and macro-F1 = 0.12; feature selection uses training-period CV only.

**14. Which are your baseline and ML models?**
Baselines: Linear Regression (regression), Logistic Regression (classification), persistence (next-day), plus mean / majority-class floors.
ML: Decision Tree, Random Forest, Gradient Boosting (HistGB – XGBoost-style), Neural Net (MLP). XGBoost is added automatically if installed.

**15. Which model is best?**
Same-day: Random Forest, Gradient Boosting and the Neural Net are practically tied (R² 0.906 / 0.908 / 0.913). By time-series CV the Neural Net is best for regression,
the Random Forest for classification; next-day: Random Forest. The differences among the top three are within noise – we say that openly.

**16. Why macro-F1 and not accuracy?**
Classes are imbalanced (Moderate 37 %, Severe 3 %). Accuracy rewards the common classes; macro-F1 weights all six equally. Class weights
and macro-F1 raised the recall of "Good" from 0.55 to 0.78.

**17. Your classification accuracy is 78 % – is that good?**
Yes: the category is a threshold of a continuous value and our regression error is ≈ 16 points, so days near a boundary flip class. 99.7 % of predictions are within one class;
only 0.3 % are off by two and none by more.

**18. Why did feature reduction work, and why did the correlation filter fail?**
PM2.5 and PM10 explain almost everything (permutation importance +42 and +13 MAE points); the other nine pollutants and all calendar features add < 2.
The filter dropped PM10 because it correlates 0.81 with PM2.5, but PM10 is the dominant pollutant in Chandigarh, Amritsar, Jaipur and Mumbai and the AQI is a **max** – so it carries unique information. PCA fails because it keeps variance, not relevance.

**19. Why does a single validation year choose a worse feature set?**
Its error curve is noisy (R² goes up and down as features are added). The 2-feature set looked better in 2018 but was worse on the test period (0.883 vs 0.908). 4-fold time-series CV gave a stable 4-feature set. We show both – and we disclose that we switched protocol after seeing this.

**20. Do festival features help prediction?**
Not for same-day AQI (the pollutants already contain the effect). For next-day forecasting they help slightly on the days they describe (Diwali-day MAE 43.3 → 40.5, n = 30) but not overall (17.64 → 17.52).

**21. Does ML really beat "tomorrow = today"?**
Random Forest MAE 17.1 vs 21.3 (−19.5 %). But AQI history alone does **not** beat persistence; the gain comes from today's individual pollutant readings. The Neural Net, and the Decision Tree / Logistic Regression for categories, do not or barely beat it.

## Cities

**22. How does Chandigarh compare?**
Sep 2019 – Jul 2020: mean AQI 97 (Delhi 216, Mumbai 110, Amritsar 112), 7.7 % bad days; PM10-dominated; Diwali 2019 raised it by 124 % (121 → 271).
Its AQI moves with Delhi (r = 0.79) and Amritsar (0.73), hardly with Mumbai (0.30).

**23. Which cities did you add and why?**
The brief says "or nearby cities": Amritsar and Gurugram (neighbours; same stubble / NCR airshed), Lucknow and Jaipur (northern belt), Bengaluru (clean reference with full history).

**24. How can you predict Chandigarh with only 10 months of data?**
We don't need its data: a model trained without it scores MAE 8.95 vs 9.12 with it. The pollutant → AQI mapping is universal; the 150-day local model is worse (14.5).

## Limitations

**25. What would you do next?**
Add weather (wind, rain, temperature, boundary-layer height; e.g. Open-Meteo / ERA5), forecast several days ahead, try LSTM / temporal CNN,
use prediction intervals, and build a small dashboard. Main limitations: no weather, ten months of Chandigarh data, Mumbai's missing AQI, the lockdown regime in the test set, hard-coded festival dates.

---
### Numbers worth memorising
26 cities · 29,531 rows · 28,157 after cleaning · 23 → 4 features · test R² 0.906 (RF) vs 0.855 (LR) · classification macro-F1 0.756 vs 0.608 · next-day MAE 17.1 vs 21.3 (persistence) · Diwali +33 pts (north +52) · lockdown −31 % · Delhi 216 vs Chandigarh 97 vs Mumbai 110.
