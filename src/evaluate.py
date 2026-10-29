"""Metrics and diagnostic plots for regression and classification."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (mean_absolute_error, mean_squared_error, r2_score, accuracy_score, balanced_accuracy_score,
                             precision_score, recall_score, f1_score, confusion_matrix)

from .config import BUCKET_ORDER


def regression_metrics(y_true, y_pred):
    return {"MAE": mean_absolute_error(y_true, y_pred),
            "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
            "R2": r2_score(y_true, y_pred)}


def classification_metrics(y_true, y_pred, labels=BUCKET_ORDER):
    order = {l: i for i, l in enumerate(labels)}
    yt = pd.Series(y_true).map(order).values
    yp = pd.Series(y_pred).map(order).values
    kw = dict(average="macro", zero_division=0, labels=labels)
    return {"accuracy": accuracy_score(y_true, y_pred),
            "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
            "precision_macro": precision_score(y_true, y_pred, **kw),
            "recall_macro": recall_score(y_true, y_pred, **kw),
            "f1_macro": f1_score(y_true, y_pred, **kw),
            "f1_weighted": f1_score(y_true, y_pred, average="weighted", zero_division=0, labels=labels),
            "within_1_class": float((np.abs(yt - yp) <= 1).mean())}


def to_rows(model, feature_set, eval_set, metrics):
    return [{"model": model, "feature_set": feature_set, "eval_set": eval_set, "metric": k, "value": v}
            for k, v in metrics.items()]


def plot_confusion(y_true, y_pred, title="", labels=BUCKET_ORDER, normalize=True, ax=None):
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    shown = cm / cm.sum(axis=1, keepdims=True).clip(min=1) if normalize else cm
    ax = ax or plt.subplots(figsize=(6.2, 5))[1]
    sns.heatmap(shown, annot=True, fmt=".2f" if normalize else "d", cmap="Blues", cbar=False,
                xticklabels=labels, yticklabels=labels, ax=ax, vmin=0, vmax=1 if normalize else None)
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual"); ax.set_title(title)
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right")
    return ax


def plot_actual_vs_pred(y_true, y_pred, title="", ax=None, lim=500):
    ax = ax or plt.subplots(figsize=(5.2, 5))[1]
    ax.scatter(y_true, y_pred, s=6, alpha=0.25)
    ax.plot([0, lim], [0, lim], "r--", lw=1)
    ax.set_xlim(0, lim); ax.set_ylim(0, lim)
    ax.set_xlabel("Actual AQI"); ax.set_ylabel("Predicted AQI"); ax.set_title(title)
    return ax


def plot_residuals(y_true, y_pred, title="", ax=None):
    res = np.asarray(y_pred) - np.asarray(y_true)
    ax = ax or plt.subplots(figsize=(5.2, 4))[1]
    sns.histplot(res, bins=60, kde=True, ax=ax)
    ax.axvline(0, color="r", ls="--", lw=1)
    ax.set_xlabel("Prediction error (pred - actual)"); ax.set_title(f"{title}  (mean {res.mean():.1f}, sd {res.std():.1f})")
    return ax
