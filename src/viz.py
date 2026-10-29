"""Plot style and figure saving."""
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns

from .config import FIG_DIR, BUCKET_COLORS, BUCKET_ORDER


def set_style():
    sns.set_theme(style="whitegrid", context="notebook", palette="deep")
    plt.rcParams.update({"figure.dpi": 100, "savefig.dpi": 130, "axes.titleweight": "bold",
                         "axes.titlesize": 12, "axes.labelsize": 10, "figure.autolayout": False})


def save_fig(name, fig=None):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig = fig or plt.gcf()
    fig.savefig(FIG_DIR / f"{name}.png", bbox_inches="tight", dpi=130)


def bucket_palette():
    return [BUCKET_COLORS[b] for b in BUCKET_ORDER]
