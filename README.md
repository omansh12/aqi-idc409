# Air Quality Prediction

**IDC409 Project · Group 14**

This project analyses and predicts the Air Quality Index (AQI) for Indian cities using daily pollutant observations from 2015 to 2020. It combines a reproducible SQLite data pipeline, exploratory data analysis (EDA), data cleaning and feature engineering, feature reduction, regression, classification, and next-day AQI forecasting.

## Project team

| Name | Roll number |
|---|---|
| Omansh Malhotra | MS23122 |
| Gyandeep Verma | MS23160 |
| Md Anas Rahman | MS23246 |

**Group number:** 14  
**Course:** IDC409

---

## 1. Start here: recommended review order

For someone reviewing the project for the first time, the recommended route is:

1. Read this README to understand the repository and workflow.
2. Open [`notebooks/01_database_pipeline.ipynb`](notebooks/01_database_pipeline.ipynb) to see how the raw CSV is loaded into SQLite and how SQL is used to clean, organise, and query the data.
3. Open [`notebooks/02_cleaning_and_features.ipynb`](notebooks/02_cleaning_and_features.ipynb) to understand the missing-value decisions, AQI validation, and feature engineering. This notebook creates the modelling table used by the later notebooks.
4. Open [`notebooks/03_EDA.ipynb`](notebooks/03_EDA.ipynb) for the exploratory analysis of pollutant distributions, AQI patterns, city differences, seasonality, and events.
5. Open [`notebooks/04_feature_reduction.ipynb`](notebooks/04_feature_reduction.ipynb) to see how the candidate features were evaluated and reduced, including PCA.
6. Open [`notebooks/05_regression_same_day.ipynb`](notebooks/05_regression_same_day.ipynb) for numerical AQI prediction.
7. Open [`notebooks/06_classification.ipynb`](notebooks/06_classification.ipynb) for AQI-category prediction.
8. Open [`notebooks/07_city_comparison_and_nextday.ipynb`](notebooks/07_city_comparison_and_nextday.ipynb) for the city-comparison extension and next-day forecasting.

**The notebooks are saved with their executed outputs.** A reviewer can open them on GitHub and inspect the code, explanations, tables, and plots without first running the project. To reproduce the work locally, follow [Running the project](#5-running-the-project).

---

## 2. Project workflow at a glance

```text
Original data: data/raw/city_day.csv
                  |
                  v
01_database_pipeline.ipynb  /  run_pipeline.py
                  |
                  v
SQLite database: db/aqi.db
(raw data, city dimension, cleaned AQI facts, audit log)
                  |
                  v
02_cleaning_and_features.ipynb
                  |
                  v
Engineered modelling data: aqi_features
(SQLite table + data/processed/aqi_features.csv)
                  |
          +-------+-------------------+
          |                           |
          v                           v
03_EDA.ipynb                 04_feature_reduction.ipynb
                                      |
                                      v
                          selected_features.json
                                      |
                  +-------------------+------------------+
                  |                   |                  |
                  v                   v                  v
          05 Regression       06 Classification    07 City comparison
                                                     + next-day forecast
                  |                   |                  |
                  +-------------------+------------------+
                                      |
                                      v
                 results/  ·  models/  ·  reports/figures/
                                      |
                                      v
                         model_results table in SQLite
```

In brief, the database stores and organises the cleaned observations. The feature-engineering stage prepares model inputs. The modelling notebooks then retrieve those inputs, train and evaluate models, save result files and trained pipelines, and log evaluation metrics in SQLite.

## 3. Repository map: where everything is located

```text
aqi-prediction/
|
|-- data/
|   |-- raw/
|   |   `-- city_day.csv
|   `-- processed/
|       `-- aqi_features.csv
|
|-- db/
|   `-- aqi.db
|
|-- sql/
|   |-- schema.sql
|   |-- clean_pipeline.sql
|   `-- queries.sql
|
|-- notebooks/
|   |-- 01_database_pipeline.ipynb
|   |-- 02_cleaning_and_features.ipynb
|   |-- 03_EDA.ipynb
|   |-- 04_feature_reduction.ipynb
|   |-- 05_regression_same_day.ipynb
|   |-- 06_classification.ipynb
|   `-- 07_city_comparison_and_nextday.ipynb
|
|-- src/
|   |-- config.py
|   |-- db.py
|   |-- pipeline.py
|   |-- features.py
|   |-- cpcb.py
|   |-- modeling.py
|   |-- evaluate.py
|   `-- viz.py
|
|-- models/                 # saved, fitted scikit-learn pipelines (.joblib)
|-- results/                # exported evaluation tables and supporting data (CSV/JSON)
|-- reports/
|   `-- figures/             # generated project figures (PNG)
|
|-- tests/
|   `-- test_core.py
|
|-- environment.yml
|-- requirements.txt
|-- README.md
|-- run_pipeline.py
`-- .gitignore
```

### Important directories and files

| Location | What it contains / why it matters |
|---|---|
| `data/raw/city_day.csv` | Original daily city-level dataset used as the input to the project. |
| `data/processed/aqi_features.csv` | Exported feature-engineered table. Useful for inspecting the final modelling data outside SQLite. |
| `db/aqi.db` | Populated SQLite database containing raw/cleaned data layers, engineered features, audit history, and model metrics. |
| `sql/schema.sql` | SQL definitions for tables, indexes, and views. |
| `sql/clean_pipeline.sql` | Named SQL cleaning and loading operations, including row deletion, zero-to-NULL conversion, and data-quality flags. |
| `sql/queries.sql` | Fourteen analytical SQL queries used to inspect and summarise the data. |
| `src/` | Reusable Python implementation shared by the notebooks and command-line pipeline. |
| `notebooks/` | Step-by-step, executed project workflow and model experiments. This is the best place to inspect the work in context. |
| `results/` | Machine-learning metrics, predictions, selected features, parameter summaries, and city/event analysis exports. |
| `models/` | Serialised fitted pipelines that can be loaded later to generate predictions. |
| `reports/figures/` | PNG figures generated by the notebooks. There are 54 figures in this folder. |
| `tests/test_core.py` | Unit tests for AQI categories, CPCB calculations, feature engineering, time splitting, and database integrity. |

## 4. What each notebook does

The notebook numbers indicate the intended execution and review order. The later modelling notebooks depend on the feature table and selected-feature information produced earlier in the workflow.

| Notebook | Main work performed | Important outputs / what to inspect |
|---|---|---|
| `01_database_pipeline.ipynb` | Inspects the raw CSV; creates the SQLite schema; imports records; performs SQL cleaning and loading; creates city metadata and festival lookup data; runs analytical queries; demonstrates database modification and rollback; checks integrity. | `db/aqi.db`, `audit_log`, `v_aqi_full`, `v_city_summary`, and query outputs. SQL definitions are in `sql/`. |
| `02_cleaning_and_features.ipynb` | Studies missingness and gap lengths; compares median imputation with MICE; applies justified missing-data handling; creates date, season, festival, lockdown, and lag features; reconstructs AQI using the CPCB formula; prepares the modelling population. | `aqi_features` table in SQLite and `data/processed/aqi_features.csv`; feature and data-quality explanations. |
| `03_EDA.ipynb` | Explores data coverage, pollutant/AQI distributions, outliers, city and regional differences, pollutant relationships, yearly/monthly/seasonal trends, weekday patterns, festivals, stubble-burning season, and lockdown period. | EDA figures in `reports/figures/` and summary values in `results/eda_key_numbers.json`. |
| `04_feature_reduction.ipynb` | Compares feature sets using correlation filtering, VIF, mutual information, permutation importance, and PCA; checks how reduction affects model performance. | `results/feature_reduction_results.csv` and `results/selected_features.json`. The selected four pollutant features are PM2.5, PM10, CO, and O3. |
| `05_regression_same_day.ipynb` | Trains models to estimate the numerical AQI for the same day from that day's pollutant and selected features; compares a mean dummy, Linear Regression, Decision Tree, Random Forest, Gradient Boosting, and MLP; evaluates errors and city/range behaviour. | `results/regression_same_day_results.csv`, `results/regression_same_day_predictions.csv`, error-by-city/range files, fitted model files, and regression figures. |
| `06_classification.ipynb` | Predicts the six CPCB AQI categories; compares a majority-class baseline, Logistic Regression, Decision Tree, Random Forest, Gradient Boosting, and MLP; studies class-wise performance, confusion matrices, ordinal errors, and robustness. | `results/classification_same_day_results.csv`, `results/classification_best_per_class.csv`, `results/classification_by_city.csv`, and classification figures. |
| `07_city_comparison_and_nextday.ipynb` | Compares Delhi, Chandigarh, Mumbai, and nearby/reference cities; examines city correlations, events, and local-vs-pooled modelling; forecasts next-day AQI value and category; compares against persistence; performs feature-group ablation and feature-importance analysis. | `results/nextday_regression_results.csv`, `results/nextday_classification_results.csv`, `results/nextday_ablation.csv`, city scorecards, next-day predictions/diagnostics, and next-day figures. |

### Reusable Python modules (`src/`)

| Module | Responsibility |
|---|---|
| `config.py` | Central paths, column names, pollutant lists, CPCB AQI bands, city/region metadata, event dates, and chronological split dates. |
| `db.py` | SQLite connections, SQL loading/execution, CSV import helpers, data access, audit logging, and model-results logging. |
| `pipeline.py` | Rebuilds the database and constructs the engineered feature table. |
| `features.py` | Calendar, season, festival, lockdown, lag, rolling, and next-day target features. |
| `cpcb.py` | CPCB pollutant sub-index and AQI reconstruction logic; used for data validation and dominant-pollutant analysis. |
| `modeling.py` | Preprocessing pipelines, model catalogues, chronological splitting, and time-series cross-validation/hyperparameter search. |
| `evaluate.py` | Regression/classification metrics and diagnostic plots such as confusion matrices and actual-vs-predicted plots. |
| `viz.py` | Shared plotting style and figure-saving utilities. |

## 5. Data and database overview

### Dataset

The input file is `data/raw/city_day.csv`. It contains daily observations for **26 Indian cities**, covering **1 January 2015 to 1 July 2020**. The original file has **29,531 rows and 16 columns**: city, date, 12 pollutant measurements, AQI, and the recorded AQI category (`AQI_Bucket`).

The dataset has uneven city/date coverage and substantial missingness in several pollutant columns. It does not include meteorological variables such as wind speed, rainfall, temperature, or boundary-layer height.

### Database structure

The SQLite database is `db/aqi.db`. Its principal tables and views are:

| Database object | Role |
|---|---|
| `raw_city_day` | Imported city-day records used by the SQL cleaning pipeline. |
| `dim_city` | City dimension table, including city, state, and region metadata. |
| `fact_aqi` | Cleaned air-quality observations linked to `dim_city`. |
| `festival_calendar` | Festival dates used by event-feature engineering and analysis. |
| `audit_log` | Records the named SQL cleaning steps, affected table/row counts, and descriptions. |
| `aqi_features` | Feature-engineered table read by the EDA and ML notebooks. |
| `model_results` | Long-form evaluation metrics logged by the model notebooks. |
| `v_aqi_full` | View joining air-quality facts with city metadata. |
| `v_city_summary` | City-level summary view. |

The database is used in the workflow: the notebooks query it for the cleaned observations and feature table, and the modelling notebooks write evaluation metrics to `model_results`. The fitted model objects themselves are saved separately under `models/`.

### Main data-quality decisions

- **1,374 completely empty rows** are deleted. The resulting raw/fact layer contains 28,157 rows.
- No duplicate `(city, date)` rows were found by the implemented duplicate check.
- Exact zero readings in CO, NOx, Benzene, Toluene, and Xylene are treated as placeholder/missing readings and changed to `NULL` based on the observed data-quality pattern.
- Impossible/out-of-range or sensor-ceiling observations are flagged rather than indiscriminately deleted.
- Ahmedabad is flagged as a suspect city because NO and CO are identical on an unusually large share of its records and its AQI values show a separate anomaly. It remains available in the database for transparency but is excluded from the main modelling population; a sensitivity analysis is also included.
- Xylene is retained in the database but excluded from model inputs because of its high missingness (approximately 61%).
- Short pollutant gaps of up to three calendar days are forward-filled per city; remaining missing predictor values are handled within model pipelines. The target AQI is not imputed for supervised learning.

For the evidence and rationale behind these decisions, see notebooks 01 and 02 and the EDA coverage/missingness sections in notebook 03.

## 6. Machine-learning tasks and evaluation

The project studies three related tasks. They should not be interpreted as the same prediction problem.

### A. Same-day AQI regression

**Question:** Given pollutant readings and selected context for a particular day, can a model estimate that day's numerical AQI?

- **Target:** `aqi`
- **Main inputs:** selected pollutant features; the final selected feature set is PM2.5, PM10, CO, and O3.
- **Models:** mean dummy baseline, Linear Regression, Decision Tree, Random Forest, histogram-based Gradient Boosting, and Multi-Layer Perceptron (MLP).
- **Metrics:** MAE, RMSE, and R².
- **Notebook:** `05_regression_same_day.ipynb`.

Because the CPCB AQI is calculated from pollutant sub-indices, same-day regression partly reconstructs an existing pollutant-to-AQI relationship. It is useful for comparing regression methods, but it is not equivalent to forecasting a future day's air quality.

### B. Same-day AQI classification

**Question:** Given the day's pollutant/context features, can a model predict its AQI category?

- **Target:** `aqi_bucket` / `AQI_Bucket`.
- **Classes:** Good, Satisfactory, Moderate, Poor, Very Poor, and Severe (all six CPCB categories).
- **Models:** majority-class dummy baseline, Logistic Regression, Decision Tree, Random Forest, histogram-based Gradient Boosting, and MLP.
- **Metrics:** accuracy, balanced accuracy, macro precision, macro recall, macro-F1, weighted-F1, confusion matrix, and proportion within one category of the true class.
- **Notebook:** `06_classification.ipynb`.

Macro-F1 is reported because the six AQI categories are imbalanced; it gives each category equal weight when averaging class-level F1 scores.

### C. Next-day AQI forecasting

**Question:** Using information available today, can a model predict tomorrow's AQI or AQI category?

- **Numeric target:** next-day AQI (`aqi_next`).
- **Categorical target:** next-day AQI category (`bucket_next`).
- **Inputs:** information available on the current day, including pollutant readings, AQI history/lag features, and relevant calendar/event features. Tomorrow's calendar fields are constructed separately where appropriate.
- **Baseline:** persistence, which predicts tomorrow's AQI/category will be the same as today's.
- **Models:** Linear Regression, Decision Tree, Random Forest, histogram-based Gradient Boosting, and classification models for the category task.
- **Metrics:** MAE, RMSE, R², skill relative to persistence, and classification metrics including macro-F1 and confusion matrix.
- **Notebook:** Part B of `07_city_comparison_and_nextday.ipynb`.

This is the project's more meaningful forecasting experiment: the target is a future observation, and the model is compared against the simple persistence assumption.

### Train/test strategy and leakage control

The main evaluation uses a **chronological split**, not a random split:

- **Training period:** dates before 1 January 2019 (2015–2018).
- **Same-day test period:** 1 January 2019 to 1 July 2020.
- **Next-day test inputs:** 1 January 2019 to 30 June 2020, with the corresponding target dates one day later.

Hyperparameter search uses `TimeSeriesSplit` within the training period, so validation folds move forward in time. Preprocessing steps such as imputation, scaling, and encoding are inside scikit-learn pipelines and are fitted on training data rather than on the held-out test data. The notebooks also include leakage sanity checks and diagnostics.

For the next-day task, training rows are restricted so that their target dates remain within the training period. The persistence baseline is evaluated on the same next-day test rows as the ML models.

## 7. Selected results

The following values are from the saved result CSVs in `results/`. They are **held-out chronological test results**, not training scores.

### Same-day regression

| Model | Test MAE ↓ | Test RMSE ↓ | Test R² ↑ |
|---|---:|---:|---:|
| Linear Regression (baseline) | 22.37 | 31.89 | 0.855 |
| Random Forest | **15.96** | 25.73 | 0.906 |
| Gradient Boosting (HistGB) | 16.05 | 25.41 | 0.908 |
| Neural Net (MLP) | 16.34 | **24.73** | **0.913** |

Random Forest has the lowest test MAE in this table, while the MLP has the highest R² and lowest RMSE. The best model therefore depends on the metric being considered.

### Same-day classification

| Model | Test accuracy ↑ | Test macro-F1 ↑ |
|---|---:|---:|
| Logistic Regression (baseline) | 0.602 | 0.608 |
| Decision Tree | 0.726 | 0.703 |
| Random Forest | **0.785** | **0.756** |
| Gradient Boosting (HistGB) | 0.761 | 0.733 |
| Neural Net (MLP) | 0.785 | 0.746 |

Random Forest achieves the highest macro-F1; Random Forest and MLP have the same rounded accuracy in the saved test results.

### Next-day regression

| Model | Test MAE ↓ | Test RMSE ↓ | Test R² ↑ |
|---|---:|---:|---:|
| Persistence (tomorrow = today) | 21.26 | 37.23 | 0.802 |
| Linear Regression | 18.91 | 29.88 | 0.873 |
| Random Forest | **17.12** | 28.15 | 0.887 |
| Gradient Boosting (HistGB) | 17.29 | **27.84** | **0.889** |
| Neural Net (MLP) | 21.72 | 32.35 | 0.851 |

Random Forest gives the lowest MAE, while Gradient Boosting has a marginally higher R² and lower RMSE. Random Forest reduces MAE by approximately **19.5% relative to the persistence baseline**.

### Next-day classification

| Approach | Test accuracy ↑ | Test macro-F1 ↑ |
|---|---:|---:|
| Persistence (today's category) | 0.737 | 0.676 |
| Random Forest | **0.774** | **0.746** |
| Gradient Boosting (HistGB) | 0.760 | 0.729 |

See the full result files for additional metrics, model comparisons, class-wise results, city-wise breakdowns, and robustness checks.

## 8. Where to find the results and figures

The project keeps both human-readable exports and the underlying fitted model pipelines.

### Main result files

| File | Contents |
|---|---|
| `results/eda_key_numbers.json` | Key numerical summaries used in EDA. |
| `results/db_audit_log.csv` | Export of the database cleaning audit log. |
| `results/selected_features.json` | Selected numeric/categorical features and feature-selection summary. |
| `results/feature_reduction_results.csv` | Performance comparison across full, filtered, PCA, and reduced feature sets. |
| `results/regression_same_day_results.csv` | Same-day regression model comparison. |
| `results/regression_same_day_predictions.csv` | Actual and predicted same-day AQI values for test observations. |
| `results/classification_same_day_results.csv` | Same-day classification model comparison. |
| `results/classification_best_per_class.csv` | Per-class precision, recall, and F1 results. |
| `results/classification_by_city.csv` | Same-day classification performance grouped by city. |
| `results/nextday_regression_results.csv` | Next-day regression model comparison against persistence. |
| `results/nextday_classification_results.csv` | Next-day category classification comparison. |
| `results/nextday_ablation.csv` | Next-day performance when different feature groups are added. |
| `results/nextday_skill_by_city.csv` | Forecast skill relative to persistence by city. |
| `results/city_comparison_table.csv` | Main like-for-like city comparison table. |
| `results/city_events.csv` | City-level event analysis output. |
| `results/city_local_vs_pooled.csv` | Local-model versus pooled-model comparison. |

Other CSV/JSON files in `results/` contain supporting diagnostics such as error by AQI range/city, parameter summaries, city correlations, lead/lag analysis, imputation experiments, and Ahmedabad sensitivity analysis.

### Figures

The 54 PNG files in `reports/figures/` are generated by the notebooks. Their filenames are prefixed by the notebook/stage number (for example, `03_` for EDA, `05_` for regression, `06_` for classification, and `07_` for city comparison/forecasting). The notebooks also show the figures in context with the code and interpretation that produced them.

### Saved trained models

The `models/` directory contains fitted scikit-learn pipelines serialised with `joblib`, including:

- `regression_linear_regression.joblib`
- `regression_gradient_boosting.joblib`
- `regression_neural_net.joblib`
- `classification_logistic_regression.joblib`
- `classification_random_forest.joblib`
- `nextday_regression_best.joblib`
- `nextday_classifier_best.joblib`

These files are fitted pipelines, not source code. The model definitions and training procedure are in `src/modeling.py` and notebooks 05–07. The saved models can be loaded with `joblib.load()` when the expected feature columns and preprocessing schema are supplied.

## 9. Running the project

### Requirements

- Python 3.9 or newer
- Packages listed in `requirements.txt`
- JupyterLab to run the notebooks
- SQLite support (included with Python through `sqlite3`)

### 9.1 Set up the environment

From the repository root (`aqi-prediction/`):

```bash
python -m venv .venv
```

Activate the environment:

```bash
# Linux / macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 9.2 Recommended: run the notebooks in order

```bash
jupyter lab
```

Open the `notebooks/` directory and execute the notebooks from `01` through `07`, in numerical order. Run each notebook from top to bottom. This route exposes the full reasoning and intermediate outputs at every stage.

**Important:** Notebook 01 rebuilds the SQLite database. Notebook 02 then creates/replaces the engineered feature table. Notebooks 04–07 depend on outputs from the earlier stages (especially the selected feature information written by notebook 04). Re-run upstream notebooks when you change the data or preprocessing logic.

### 9.3 Alternative: build the data pipeline without notebooks 01 and 02

The command-line pipeline performs the database build and feature-table generation in one step:

```bash
python run_pipeline.py
```

By default, it rebuilds `db/aqi.db` and writes `data/processed/aqi_features.csv`, as well as the `aqi_features` table in SQLite. It does **not** train the ML models or regenerate the EDA/model results. After it finishes, open JupyterLab and run notebooks `03_EDA.ipynb` through `07_city_comparison_and_nextday.ipynb` in order.

Optional custom input/output paths:

```bash
python run_pipeline.py --csv data/raw/city_day.csv --db /tmp/aqi.db --out /tmp/aqi_features.csv
```

**Do not run the headless pipeline and notebook 01 unless you intend to rebuild the database twice.** Both routes rebuild the database from the raw CSV; choose one route for the data-preparation stage.

### 9.4 Run the tests

From the repository root:

```bash
python -m unittest discover -s tests -v
```

The unit tests cover CPCB AQI bands and sub-index completeness, event windows, calendar-day lag construction, chronological splitting, database row counts and integrity, placeholder-zero handling, audit logging, SQL query execution, and the engineered feature table.

## 10. Interpretation and limitations

- **Same-day prediction is partly reconstructive.** CPCB AQI is derived from pollutant sub-indices, so high same-day prediction performance does not by itself demonstrate the ability to forecast future pollution.
- **Next-day forecasting is the stronger predictive test**, but it is still limited by the available features and observation coverage.
- **No meteorological inputs are available.** Wind, rainfall, temperature, humidity, and boundary-layer height could materially improve forecasting.
- **City coverage is uneven.** Chandigarh has observations only from September 2019 onward, and Mumbai has substantial missingness in AQI. City-level comparisons must therefore use matched date windows where possible.
- **The test period includes the COVID-19 lockdown.** This is a distinct pollution regime and can affect held-out model performance.
- **Ahmedabad is flagged as suspect** based on the data-quality checks described above; conclusions from the main models do not represent that city.
- **Festival indicators are manually configured** in `src/config.py`. Their dates/windows are assumptions used for analysis and should be verified against authoritative calendars if the project is extended.
- **The dataset is observational and city-day aggregated.** The models do not establish causal effects of festivals, lockdowns, or individual pollutants.


