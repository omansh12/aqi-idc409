"""Pre-processing pipelines, model catalogue and tuning helpers (no information leaks from test data)."""
import time
import warnings

import numpy as np
import pandas as pd
from scipy.stats import loguniform
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.decomposition import PCA
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import (HistGradientBoostingClassifier, HistGradientBoostingRegressor,
                              RandomForestClassifier, RandomForestRegressor)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from .config import RANDOM_STATE

try:                                    # optional dependency: pip install xgboost
    from xgboost import XGBRegressor
    HAS_XGB = True
except Exception:                       # pragma: no cover
    HAS_XGB = False


# ----------------------------------------------------------------------------- pre-processing
def make_preprocessor(numeric_cols, categorical_cols=(), kind="tree", pca_cols=None, n_pca=None):
    """kind='tree'   : NaNs are passed through (tree models in scikit-learn handle them natively)
       kind='linear' : median imputation + StandardScaler, fitted on TRAIN only
                       (MICE / IterativeImputer was tested: no accuracy gain and less robust, see notebook 02)
       pca_cols/n_pca: replace these numeric columns by `n_pca` principal components (linear kind only)"""
    numeric_cols, categorical_cols = list(numeric_cols), list(categorical_cols)
    parts = []

    def linear_block(cols):
        return Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])

    if pca_cols:
        pca_cols = list(pca_cols)
        rest = [c for c in numeric_cols if c not in pca_cols]
        pipe = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler()),
                         ("pca", PCA(n_components=n_pca, random_state=RANDOM_STATE))])
        parts.append(("pca", pipe, pca_cols))
        if rest:
            parts.append(("num", Pipeline([("scale", StandardScaler())]), rest))
    elif numeric_cols:
        parts.append(("num", linear_block(numeric_cols) if kind == "linear" else "passthrough", numeric_cols))
    if categorical_cols:
        parts.append(("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_cols))
    return ColumnTransformer(parts, remainder="drop")


def make_pipeline(estimator, numeric_cols, categorical_cols=(), kind="tree", **kw):
    return Pipeline([("prep", make_preprocessor(numeric_cols, categorical_cols, kind, **kw)), ("model", estimator)])


# ----------------------------------------------------------------------------- model catalogue
def regression_catalog(n_jobs=-1):
    cat = {
        "Mean (dummy)": dict(est=DummyRegressor(strategy="mean"), kind="tree", space=None),
        "Linear Regression": dict(est=LinearRegression(), kind="linear", space=None),
        "Decision Tree": dict(est=DecisionTreeRegressor(random_state=RANDOM_STATE), kind="tree",
                              space={"model__max_depth": [4, 6, 8, 10, 14, None],
                                     "model__min_samples_leaf": [1, 5, 10, 20, 40]}),
        "Random Forest": dict(est=RandomForestRegressor(n_estimators=120, max_samples=0.7, n_jobs=n_jobs,
                                                         random_state=RANDOM_STATE), kind="tree",
                              space={"model__max_depth": [12, 20, None], "model__min_samples_leaf": [1, 3, 5],
                                     "model__max_features": [0.33, 0.5, 0.8]}),
        "Gradient Boosting (HistGB)": dict(est=HistGradientBoostingRegressor(max_iter=300, random_state=RANDOM_STATE),
                                           kind="tree",
                                           space={"model__learning_rate": [0.03, 0.05, 0.1],
                                                  "model__max_leaf_nodes": [15, 31, 63],
                                                  "model__min_samples_leaf": [20, 50],
                                                  "model__l2_regularization": [0.0, 1.0]}),
        "Neural Net (MLP)": dict(est=TransformedTargetRegressor(
            regressor=MLPRegressor(hidden_layer_sizes=(64, 32), early_stopping=True, max_iter=400,
                                   random_state=RANDOM_STATE), transformer=StandardScaler()),
            kind="linear", space=None),
    }
    if HAS_XGB:
        cat["XGBoost"] = dict(est=XGBRegressor(n_estimators=300, tree_method="hist", random_state=RANDOM_STATE, n_jobs=n_jobs),
                              kind="tree", space={"model__max_depth": [3, 5, 7], "model__learning_rate": [0.03, 0.05, 0.1],
                                                  "model__subsample": [0.7, 1.0]})
    return cat


def classification_catalog(n_jobs=-1):
    cat = {
        "Majority class (dummy)": dict(est=DummyClassifier(strategy="most_frequent"), kind="tree", space=None),
        "Logistic Regression": dict(est=LogisticRegression(max_iter=3000, class_weight="balanced"), kind="linear", space=None),
        "Decision Tree": dict(est=DecisionTreeClassifier(class_weight="balanced", random_state=RANDOM_STATE), kind="tree",
                              space={"model__max_depth": [4, 6, 8, 10, 14, None],
                                     "model__min_samples_leaf": [1, 5, 10, 20, 40]}),
        "Random Forest": dict(est=RandomForestClassifier(n_estimators=120, max_samples=0.7, n_jobs=n_jobs,
                                                          class_weight="balanced_subsample", random_state=RANDOM_STATE),
                              kind="tree", space={"model__max_depth": [12, 20, None], "model__min_samples_leaf": [1, 3, 5],
                                                  "model__max_features": ["sqrt", 0.5]}),
        "Gradient Boosting (HistGB)": dict(est=HistGradientBoostingClassifier(max_iter=150, class_weight="balanced",
                                                                              random_state=RANDOM_STATE), kind="tree",
                                           space={"model__learning_rate": [0.05, 0.1, 0.15],
                                                  "model__max_leaf_nodes": [15, 31],
                                                  "model__min_samples_leaf": [20, 50],
                                                  "model__l2_regularization": [0.0, 1.0]}),
        "Neural Net (MLP)": dict(est=MLPClassifier(hidden_layer_sizes=(64, 32), alpha=1e-3, max_iter=300,
                                                   random_state=RANDOM_STATE), kind="linear", space=None),
    }
    return cat


# ----------------------------------------------------------------------------- data split
def time_split(df, cutoff, date_col="date"):
    """Chronological split: rows before `cutoff` -> train, the rest -> test (never shuffle time series)."""
    cutoff = pd.Timestamp(cutoff)
    return df[df[date_col] < cutoff].copy(), df[df[date_col] >= cutoff].copy()


# ----------------------------------------------------------------------------- tuning
def fit_model(name, spec, numeric_cols, categorical_cols, X_train, y_train, scoring, n_iter=6, n_splits=3,
              encode_target=None, verbose=True):
    """Fit one model. Models with a search space are tuned with RandomizedSearchCV + TimeSeriesSplit.
    X_train MUST be sorted by date so that every CV fold validates on a later period than it trains on."""
    pipe = make_pipeline(spec["est"], numeric_cols, categorical_cols, spec["kind"])
    t0 = time.time()
    info = {"model": name, "best_params": {}, "cv_score": np.nan}
    y = y_train if encode_target is None else encode_target(y_train)
    if spec["space"]:
        space = spec["space"]
        total = int(np.prod([len(v) for v in space.values()]))
        search = RandomizedSearchCV(pipe, space, n_iter=min(n_iter, total), cv=TimeSeriesSplit(n_splits=n_splits),
                                    scoring=scoring, random_state=RANDOM_STATE, n_jobs=1, refit=True, error_score="raise")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            search.fit(X_train, y)
        best, info["best_params"] = search.best_estimator_, {k.replace("model__", ""): v for k, v in search.best_params_.items()}
        info["cv_score"] = search.best_score_
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            best = pipe.fit(X_train, y)
    info["fit_seconds"] = round(time.time() - t0, 1)
    if verbose:
        print(f"  {name:<28} fitted in {info['fit_seconds']:>6.1f}s   best params: {info['best_params'] or '-'}")
    return best, info


def feature_names_after_prep(pipe):
    try:
        return list(pipe.named_steps["prep"].get_feature_names_out())
    except Exception:
        return None
