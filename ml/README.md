# ML

## Composants

| Dossier | Rôle |
|---------|------|
| `training/` | Scripts d'entraînement XGBoost + Autoencoder |
| `models/` | Artefacts modèles (ignorés par git, versionnés via MLflow) |
| `api/` | FastAPI — endpoint POST /score |

## API Scoring

```
POST /score
Content-Type: application/json

{
  "transaction_id": "...",
  "features": { ... }
}

→ { "transaction_id": "...", "score": 0.82, "is_alert": true }
```

## Seuil d'alerte

Configurable via `RISK_THRESHOLD` dans `.env` (défaut : 0.7).
