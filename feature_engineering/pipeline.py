"""
Pipeline de feature engineering AML — Dataset UEMOA.

Point d'entrée unique : compute_features()
Utilisé par ml/training/train.py et par l'API de scoring en inférence.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

from feature_engineering.features.window_sender     import compute_window_sender
from feature_engineering.features.receiver_diversity import compute_receiver_diversity
from feature_engineering.features.contact_graph      import compute_contact_graph
from feature_engineering.features.balance_features   import compute_balance_features

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

CATEGORICAL_COLS = [
    "type",
    "sender_bank_country",
    "receiver_bank_country",
    "sender_bank_code",
    "receiver_bank_code",
]

COLS_TO_DROP = [
    "transaction_id",
    "txn_timestamp",
    "datetime",
    "is_fraud",
    "fraud_type",
    "new_balance_sender",
    "new_balance_receiver",
    "step",
    "sender_account_id",
    "receiver_account_id",
]


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _parse_datetime(df: pd.DataFrame) -> pd.DataFrame:
    """Parse txn_timestamp et trie le DataFrame par ordre chronologique."""
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["txn_timestamp"], format="%m/%d/%Y %H:%M")
    df = df.sort_values("datetime").reset_index(drop=True)
    return df


def _compute_static_features(df: pd.DataFrame) -> pd.DataFrame:
    """Features statiques calculées ligne par ligne, sans fenêtre temporelle."""
    df = df.copy()

    # Heure de nuit : 22h–05h
    df["is_night"] = (
        (df["hour_of_day"] >= 22) | (df["hour_of_day"] <= 5)
    ).astype("int8")

    # Transaction transfrontalière
    df["is_cross_border"] = (
        df["sender_bank_country"] != df["receiver_bank_country"]
    ).astype("int8")

    # Montant log-transformé
    df["amount_log"] = np.log1p(df["amount_xof"]).astype("float32")

    return df


def encode_categoricals(
    df: pd.DataFrame,
    encoders: dict = None,
    fit: bool = True,
) -> tuple[pd.DataFrame, dict]:
    """
    Encode les colonnes catégorielles avec LabelEncoder.

    Args:
        df       : DataFrame à encoder (modifié en place).
        encoders : dict existant (pour l'inférence). None si fit=True.
        fit      : True lors de l'entraînement, False lors de l'inférence.

    Returns:
        (df_encodé, encoders_dict)
    """
    df = df.copy()
    if fit:
        encoders = {}

    for col in CATEGORICAL_COLS:
        if fit:
            le = LabelEncoder()
            df[col + "_enc"] = le.fit_transform(df[col].astype(str))
            encoders[col] = le
        else:
            le = encoders[col]
            # Gérer les valeurs inconnues : remplacer par la première classe connue
            known = set(le.classes_)
            df[col + "_safe"] = df[col].astype(str).where(
                df[col].astype(str).isin(known),
                other=le.classes_[0],
            )
            df[col + "_enc"] = le.transform(df[col + "_safe"])
            df = df.drop(columns=[col + "_safe"], inplace=False)

    return df, encoders


# ---------------------------------------------------------------------------
# Point d'entrée principal
# ---------------------------------------------------------------------------

def compute_features(
    df: pd.DataFrame,
    encoders: dict = None,
    fit_encoders: bool = True,
) -> tuple[pd.DataFrame, dict]:
    """
    Pipeline complet : DataFrame brut UEMOA → DataFrame enrichi.

    Args:
        df            : DataFrame avec les 19 colonnes du dataset UEMOA.
        encoders      : dict d'encoders LabelEncoder pré-fittés (inférence uniquement).
        fit_encoders  : True pour entraînement, False pour inférence.

    Returns:
        (df_enrichi, encoders_dict)
    """
    print("[pipeline] Parsing datetime...")
    df = _parse_datetime(df)

    print("[pipeline] Features statiques...")
    df = _compute_static_features(df)

    print("[pipeline] Features de balance...")
    df = compute_balance_features(df)

    print("[pipeline] Fenêtres temporelles émetteur (30j/24h/1h)...")
    df = compute_window_sender(df)

    print("[pipeline] Diversité des récepteurs (7j)...")
    df = compute_receiver_diversity(df)

    print("[pipeline] Graphe de contact (first_contact, round_trip)...")
    df = compute_contact_graph(df)

    print("[pipeline] Encodage catégoriels...")
    df, encoders = encode_categoricals(df, encoders=encoders, fit=fit_encoders)

    print(f"[pipeline] Terminé — shape : {df.shape}")
    return df, encoders


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """
    Retourne la liste des colonnes à utiliser comme features X pour le modèle.
    Exclut les identifiants, la cible, et les colonnes post-transaction.
    """
    exclude = set(COLS_TO_DROP) | set(CATEGORICAL_COLS)
    return [c for c in df.columns if c not in exclude]
