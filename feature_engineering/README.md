# Feature Engineering

Ce module calcule les features comportementales qui alimentent le modèle ML.

## Composants

| Fichier | Rôle |
|---------|------|
| `pipeline.py` | Fonction principale : DataFrame brut → DataFrame enrichi |
| `features/` | Fonctions de calcul par feature (optionnel, découpage futur) |

## User Story couverte

- **US-14** : Feature Engineering

## Features calculées

| Feature | Description |
|---------|-------------|
| `ratio_amount_avg` | Montant / moyenne des 30 derniers jours du compte |
| `amount_std` | Écart-type des montants sur 30 jours |
| `tx_count_24h` | Nombre de transactions dans les 24 dernières heures |
| `velocity_1h` | Montant cumulé sur la dernière heure |
| `is_night` | 1 si transaction entre 22h et 6h |
| `is_first_contact` | 1 si première transaction vers ce receiver_id |
| `distinct_receivers` | Nb de bénéficiaires distincts sur 7 jours |
| `is_round_trip` | 1 si A→B et B→A dans les 24h |

## Utilisation

```python
import pandas as pd
from feature_engineering.pipeline import compute_features

df_raw = pd.read_csv("data/synthetic/transactions.csv")
df_features = compute_features(df_raw)
```

## Tests

```bash
pytest tests/unit/test_feature_engineering.py -v
```
