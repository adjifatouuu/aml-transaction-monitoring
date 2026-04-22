"""
API de scoring AML — FastAPI.

Endpoints :
    GET  /health                  → statut du service + version du modèle
    GET  /alerts                  → liste des alertes (filtrable)
    GET  /transactions            → liste des transactions (paginable)
    GET  /transactions/{id}       → détail d'une transaction
    POST /score                   → score de risque pour une transaction brute
    POST /score/batch             → score pour un lot de transactions

Usage (via Docker) :
    docker-compose up -d scoring-api
    curl http://localhost:8000/health
"""

import json
import os
import pickle
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# Rendre les modules du projet importables
sys.path.insert(0, "/app")

from feature_engineering.pipeline import compute_features, get_feature_columns

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_PATH     = os.environ.get("MODEL_PATH",    "ml/models/xgboost_v1.pkl")
RISK_THRESHOLD = float(os.environ.get("RISK_THRESHOLD", "0.5"))
SEEDS_DIR      = os.path.join(os.path.dirname(__file__), "seeds")

# ---------------------------------------------------------------------------
# État global (chargé au démarrage)
# ---------------------------------------------------------------------------

_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Charge le modèle et les seeds au démarrage du serveur."""
    # Modèle ML
    print(f"[startup] Chargement du modèle depuis {MODEL_PATH}...")
    try:
        with open(MODEL_PATH, "rb") as f:
            artifact = pickle.load(f)
        _state["model"]        = artifact["model"]
        _state["encoders"]     = artifact["encoders"]
        _state["feature_cols"] = artifact["feature_cols"]
        print(f"[startup] Modèle chargé — {len(_state['feature_cols'])} features")
    except FileNotFoundError:
        print(f"[startup] AVERTISSEMENT : modèle non trouvé à {MODEL_PATH}")
        print("[startup] L'endpoint /score retournera 503 jusqu'au chargement du modèle.")

    # Seeds (alertes + transactions)
    for key, filename in [("alerts", "alerts.json"), ("transactions", "transactions.json")]:
        seed_path = os.path.join(SEEDS_DIR, filename)
        try:
            with open(seed_path, encoding="utf-8") as f:
                _state[key] = json.load(f)
            print(f"[startup] Seeds '{key}' chargées — {len(_state[key])} entrées")
        except FileNotFoundError:
            print(f"[startup] AVERTISSEMENT : seed non trouvée à {seed_path}")
            _state[key] = []

    yield
    _state.clear()


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AML Scoring API",
    description="Score de risque de blanchiment pour les transactions UEMOA",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schémas Pydantic — Scoring
# ---------------------------------------------------------------------------

class TransactionIn(BaseModel):
    """Contrat d'entrée — correspond aux colonnes brutes du dataset UEMOA."""

    transaction_id:      str   = Field(..., example="txn-abc-123")
    step:                int   = Field(..., example=0)
    type:                str   = Field(..., example="VIREMENT")
    amount_xof:          float = Field(..., gt=0, example=250000.0)
    sender_account_id:   str   = Field(..., example="SN1234567890")
    sender_bank_country: str   = Field(..., example="SN")
    sender_bank_code:    str   = Field(..., example="CBAO")
    receiver_account_id: str   = Field(..., example="CI9876543210")
    receiver_bank_country: str = Field(..., example="CI")
    receiver_bank_code:  str   = Field(..., example="NSIA")
    old_balance_sender:  float = Field(..., ge=0, example=500000.0)
    old_balance_receiver: float = Field(..., ge=0, example=1200000.0)
    txn_timestamp:       str   = Field(..., example="4/21/2024 14:35")
    hour_of_day:         int   = Field(..., ge=0, le=23, example=14)
    day_of_week:         int   = Field(..., ge=0, le=6, example=0)
    new_balance_sender:  float = Field(..., ge=0, example=250000.0)
    new_balance_receiver: float = Field(..., ge=0, example=1450000.0)

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        allowed = {"VIREMENT", "MOBILE_MONEY", "RETRAIT", "PAIEMENT", "DEPOT"}
        if v.upper() not in allowed:
            raise ValueError(f"type doit être parmi {allowed}")
        return v.upper()

    @field_validator("txn_timestamp")
    @classmethod
    def validate_timestamp(cls, v):
        try:
            pd.to_datetime(v, format="%m/%d/%Y %H:%M")
        except Exception:
            raise ValueError("txn_timestamp doit être au format MM/DD/YYYY HH:MM")
        return v


class ScoreOut(BaseModel):
    transaction_id: str
    score:          float = Field(..., ge=0.0, le=1.0, description="Score de risque (0=normal, 1=fraude)")
    is_alert:       bool  = Field(..., description=f"True si score >= RISK_THRESHOLD ({RISK_THRESHOLD})")
    risk_level:     str   = Field(..., description="critique | élevé | moyen | faible")
    threshold_used: float


class BatchIn(BaseModel):
    transactions: list[TransactionIn]


class BatchOut(BaseModel):
    results: list[ScoreOut]
    total:   int
    alerts:  int


# ---------------------------------------------------------------------------
# Schémas Pydantic — Données (alertes / transactions)
# ---------------------------------------------------------------------------

class AlertOut(BaseModel):
    alert_id:       str
    transaction_id: str
    account_id:     str
    amount:         float
    currency:       str
    score:          float
    risk_level:     str
    status:         str
    created_at:     str
    assigned_to:    Optional[str]
    flags:          list[str]


class TransactionOut(BaseModel):
    transaction_id:   str
    account_id:       str
    receiver_id:      str
    amount:           float
    currency:         str
    timestamp:        str
    transaction_type: str
    channel:          str
    sender_country:   str
    receiver_country: str
    score:            float
    label:            int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _score_to_level(score: float) -> str:
    if score >= 0.9:  return "critique"
    if score >= 0.7:  return "élevé"
    if score >= 0.5:  return "moyen"
    return "faible"


def _predict(transactions: list[dict]) -> list[float]:
    """
    Transforme une liste de dicts transaction en scores de risque.
    Applique le même pipeline de features que l'entraînement.
    """
    if "model" not in _state:
        raise HTTPException(status_code=503, detail="Modèle non chargé — relancer le service.")

    df = pd.DataFrame(transactions)

    # Appliquer le feature engineering avec les encoders pré-fittés
    df_feat, _ = compute_features(
        df,
        encoders=_state["encoders"],
        fit_encoders=False,
    )

    # Sélectionner uniquement les features attendues par le modèle
    X = df_feat[_state["feature_cols"]]

    scores = _state["model"].predict_proba(X)[:, 1]
    return scores.tolist()


# ---------------------------------------------------------------------------
# Endpoints — Monitoring
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Monitoring"])
def health():
    """Vérifie que le service est opérationnel et que le modèle est chargé."""
    model_loaded = "model" in _state
    return {
        "status":       "ok" if model_loaded else "degraded",
        "model_loaded": model_loaded,
        "n_features":   len(_state.get("feature_cols", [])),
        "threshold":    RISK_THRESHOLD,
        "timestamp":    datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Endpoints — Données
# ---------------------------------------------------------------------------

@app.get("/alerts", response_model=list[AlertOut], tags=["Données"])
def get_alerts(
    status:     Optional[str] = Query(None, description="ouverte | en_cours | clôturée"),
    risk_level: Optional[str] = Query(None, description="critique | élevé | moyen | faible"),
    days:       int           = Query(30,   description="Fenêtre temporelle en jours"),
):
    """
    Retourne la liste des alertes, filtrables par statut, niveau de risque et période.
    """
    alerts = _state.get("alerts", [])

    # Filtre temporel
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    alerts = [
        a for a in alerts
        if datetime.fromisoformat(a["created_at"].replace("Z", "+00:00")) >= cutoff
    ]

    if status:
        alerts = [a for a in alerts if a["status"] == status]
    if risk_level:
        alerts = [a for a in alerts if a["risk_level"] == risk_level]

    return alerts


@app.get("/transactions", response_model=list[TransactionOut], tags=["Données"])
def get_transactions(
    limit:      int           = Query(100, ge=1, le=500, description="Nombre max de transactions"),
    offset:     int           = Query(0,   ge=0,          description="Décalage pour la pagination"),
    account_id: Optional[str] = Query(None,               description="Filtrer par compte émetteur"),
):
    """Retourne la liste paginée des transactions, filtrables par compte émetteur."""
    txs = _state.get("transactions", [])
    if account_id:
        txs = [t for t in txs if t["account_id"] == account_id]
    return txs[offset : offset + limit]


@app.get("/transactions/{transaction_id}", response_model=TransactionOut, tags=["Données"])
def get_transaction(transaction_id: str):
    """Retourne le détail d'une transaction par son identifiant."""
    txs = _state.get("transactions", [])
    tx = next((t for t in txs if t["transaction_id"] == transaction_id), None)
    if tx is None:
        raise HTTPException(status_code=404, detail=f"Transaction '{transaction_id}' introuvable.")
    return tx


# ---------------------------------------------------------------------------
# Endpoints — Scoring
# ---------------------------------------------------------------------------

@app.post("/score", response_model=ScoreOut, tags=["Scoring"])
def score_transaction(transaction: TransactionIn):
    """
    Calcule le score de risque AML pour une transaction.

    Retourne un score entre 0 (normal) et 1 (fraude certaine),
    et déclenche une alerte si le score dépasse le seuil configuré.
    """
    scores = _predict([transaction.model_dump()])
    s = scores[0]

    return ScoreOut(
        transaction_id=transaction.transaction_id,
        score=round(s, 4),
        is_alert=s >= RISK_THRESHOLD,
        risk_level=_score_to_level(s),
        threshold_used=RISK_THRESHOLD,
    )


@app.post("/score/batch", response_model=BatchOut, tags=["Scoring"])
def score_batch(batch: BatchIn):
    """
    Calcule les scores pour un lot de transactions en une seule requête.
    Maximum 500 transactions par appel.
    """
    if len(batch.transactions) > 500:
        raise HTTPException(status_code=400, detail="Maximum 500 transactions par appel batch.")

    tx_dicts = [t.model_dump() for t in batch.transactions]
    scores   = _predict(tx_dicts)

    results = [
        ScoreOut(
            transaction_id=tx["transaction_id"],
            score=round(s, 4),
            is_alert=s >= RISK_THRESHOLD,
            risk_level=_score_to_level(s),
            threshold_used=RISK_THRESHOLD,
        )
        for tx, s in zip(tx_dicts, scores)
    ]

    return BatchOut(
        results=results,
        total=len(results),
        alerts=sum(1 for r in results if r.is_alert),
    )
