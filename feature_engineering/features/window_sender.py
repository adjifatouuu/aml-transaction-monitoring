"""
Features comportementales par fenêtre temporelle glissante sur le compte émetteur.

Approche : groupby + apply par sender pour éviter les conflits d'index
dupliqués (plusieurs transactions à la même minute = même datetime index).

Toutes les agrégations appliquent shift(1) pour exclure la transaction
courante du calcul (anti-leakage).
"""

import warnings

import numpy as np
import pandas as pd


def _rolling_for_sender(group: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les 4 features de fenêtre pour un seul compte émetteur.
    Appelé par groupby().apply() — taille moyenne ~23 lignes sur ce dataset.
    """
    group    = group.sort_values("datetime")
    orig_idx = group.index
    g        = group.set_index("datetime")
    amount   = g["amount_xof"]

    mean_30d = amount.rolling("30D").mean().shift(1)
    std_30d  = amount.rolling("30D").std().shift(1)
    cnt_24h  = amount.rolling("24h").count().shift(1)
    sum_1h   = amount.rolling("1h").sum().shift(1)

    result = pd.DataFrame(
        {
            "ratio_amount_avg": (amount / mean_30d.replace(0, np.nan)).values,
            "amount_std":       std_30d.values,
            "tx_count_24h":     cnt_24h.values,
            "velocity_1h":      sum_1h.values,
        },
        index=orig_idx,
    )
    return result


def compute_window_sender(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les features de fenêtre temporelle par compte émetteur.

    Requiert que 'datetime' (pd.Timestamp) soit déjà présent dans df.

    Features ajoutées :
        - ratio_amount_avg  : amount_xof / moyenne glissante 30 jours
        - amount_std        : écart-type glissant 30 jours
        - tx_count_24h      : nb de transactions dans les 24h précédentes
        - velocity_1h       : montant cumulé envoyé dans la dernière heure
    """
    df = df.copy()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        feat = df.groupby("sender_account_id", group_keys=False).apply(
            _rolling_for_sender
        )

    df["ratio_amount_avg"] = feat["ratio_amount_avg"].fillna(1.0).astype("float32")
    df["amount_std"]       = feat["amount_std"].fillna(0.0).astype("float32")
    df["tx_count_24h"]     = feat["tx_count_24h"].fillna(1).astype("int16")
    df["velocity_1h"]      = feat["velocity_1h"].fillna(df["amount_xof"]).astype("float32")

    return df
