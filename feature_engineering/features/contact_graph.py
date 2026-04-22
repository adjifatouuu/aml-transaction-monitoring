"""
Features de graphe de transactions :
    - is_first_contact : 1 si première transaction vers ce receiver_account_id
    - is_round_trip    : 1 si A→B et B→A dans les 24h
"""

import pandas as pd


def compute_contact_graph(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ajoute 'is_first_contact' et 'is_round_trip'.

    Requiert que df soit trié par 'datetime' ASC.
    """
    df = df.copy()

    # ------------------------------------------------------------------
    # is_first_contact : première transaction de cet émetteur vers ce récepteur
    # ------------------------------------------------------------------
    df["_pair"] = df["sender_account_id"] + "_" + df["receiver_account_id"]
    df["is_first_contact"] = (
        (~df.duplicated(subset=["_pair"], keep="first")).astype("int8")
    )
    df = df.drop(columns=["_pair"])

    # ------------------------------------------------------------------
    # is_round_trip : A→B et B→A dans les 24h (86 400 secondes)
    # Pré-filtrage par bucket date pour éviter un produit cartésien.
    # ------------------------------------------------------------------
    df["_date_bucket"] = df["datetime"].dt.date

    # Construire les arêtes inversées : pour chaque B→A, créer une ligne "A→B inversée"
    rev = (
        df[["sender_account_id", "receiver_account_id",
            "transaction_id", "datetime", "_date_bucket"]]
        .rename(columns={
            "sender_account_id":   "_rev_receiver",   # B (émetteur original)
            "receiver_account_id": "_rev_sender",     # A (récepteur original)
            "datetime":            "datetime_rev",
            "transaction_id":      "transaction_id_rev",
        })
    )
    # rev._rev_sender=A, rev._rev_receiver=B  →  correspond à l'arête A→B inverse de B→A

    merged = df.merge(
        rev,
        left_on=["sender_account_id", "receiver_account_id", "_date_bucket"],
        right_on=["_rev_sender",       "_rev_receiver",       "_date_bucket"],
        how="left",
    )

    merged["is_round_trip"] = (
        merged["transaction_id_rev"].notna()
        & (merged["transaction_id"] != merged["transaction_id_rev"])
        & (
            (merged["datetime"] - merged["datetime_rev"])
            .abs()
            .dt.total_seconds()
            <= 86_400
        )
    ).astype("int8")

    # Garder le max par transaction (plusieurs matches possibles)
    rt = merged.groupby("transaction_id")["is_round_trip"].max()
    df["is_round_trip"] = df["transaction_id"].map(rt).fillna(0).astype("int8")
    df = df.drop(columns=["_date_bucket"])

    return df
