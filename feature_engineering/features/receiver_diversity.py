"""
Feature : distinct_receivers_7d

Nombre de récepteurs distincts contactés par l'émetteur dans les 7 derniers jours.
Utilise une agrégation quotidienne intermédiaire pour éviter rolling().apply(nunique)
qui est O(n²) et inutilisable sur des datasets volumineux.
"""

import pandas as pd


def compute_receiver_diversity(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ajoute la colonne 'distinct_receivers_7d'.

    Requiert que df contienne 'sender_account_id', 'receiver_account_id' et 'datetime'.
    """
    df = df.copy()
    df["_date"] = df["datetime"].dt.date

    # 1. Agréger : nb récepteurs distincts par (sender, jour)
    daily = (
        df.groupby(["sender_account_id", "_date"])["receiver_account_id"]
        .nunique()
        .reset_index(name="_daily_rcv")
    )

    # 2. Rolling 7 jours sur la série quotidienne (2000 comptes × ~253 jours max)
    daily["_date"] = pd.to_datetime(daily["_date"])
    daily = daily.sort_values(["sender_account_id", "_date"])
    daily = daily.set_index("_date")

    rolling = (
        daily.groupby("sender_account_id")["_daily_rcv"]
        .rolling("7D", min_periods=1)
        .sum()
        .reset_index()
    )
    rolling.columns = ["sender_account_id", "_date", "distinct_receivers_7d"]
    rolling["_date"] = rolling["_date"].dt.date

    # 3. Merge retour sur df
    df = df.merge(rolling, on=["sender_account_id", "_date"], how="left")
    df["distinct_receivers_7d"] = df["distinct_receivers_7d"].fillna(1).astype("int16")
    df = df.drop(columns=["_date"])

    return df
