"""
Features dérivées des colonnes de balance.

Ces colonnes sont présentes dans le dataset UEMOA mais absentes des datasets
génériques — elles apportent un signal fort pour détecter la fraude.
"""

import numpy as np
import pandas as pd


def compute_balance_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ajoute les features de balance suivantes :
        - delta_balance_sender   : montant réellement débité du compte émetteur
        - balance_ratio          : fraction du solde envoyée (amount / old_balance)
        - is_zero_out_sender     : 1 si le solde final de l'émetteur est quasi-nul (<= 500 XOF)
        - balance_jump_receiver  : ratio new_balance / old_balance du récepteur

    ⚠️ new_balance_sender et new_balance_receiver ne sont PAS inclus dans X
    (post-transaction = leakage). Ces features en sont dérivées de façon
    interprétable, et seront exclues des features brutes lors du training.
    """
    df = df.copy()

    df["delta_balance_sender"] = (
        (df["old_balance_sender"] - df["new_balance_sender"]).astype("float32")
    )

    df["balance_ratio"] = (
        df["amount_xof"] / df["old_balance_sender"].replace(0, np.nan)
    ).fillna(0.0).astype("float32")

    df["is_zero_out_sender"] = (df["new_balance_sender"] <= 500).astype("int8")

    df["balance_jump_receiver"] = (
        df["new_balance_receiver"] / df["old_balance_receiver"].replace(0, np.nan)
    ).fillna(1.0).astype("float32")

    return df
