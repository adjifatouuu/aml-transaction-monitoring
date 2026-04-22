# AML Transaction Monitoring

Système de détection automatique du blanchiment d'argent (AML) pour les institutions financières de la zone UEMOA, régulées par la BCEAO.

## Vue d'ensemble

Le pipeline analyse les transactions financières en quasi-temps réel, calcule un score de risque via Machine Learning, et alerte les équipes compliance dès qu'une transaction est suspecte.

## Architecture

```
Transactions  →  Ingestion  →  Feature Engineering
                                       ↓
                                   Scoring ML
                                       ↓
                                   Alerting
                                       ↓
                             Interface Compliance
```

## Stack technique

| Couche            | Technologies                     |
|-------------------|----------------------------------|
| Ingestion         | Apache Kafka, Debezium            |
| Stockage          | MinIO (Bronze / Silver / Gold)   |
| Transformation    | Apache Spark, dbt                |
| Orchestration     | Apache Airflow                   |
| ML Tracking       | MLflow                           |
| API Scoring       | FastAPI (Python)                 |
| Frontend          | React + Tailwind CSS             |
| Infra locale      | Docker Compose                   |

## Contrat de données

```json
{
  "transaction_id"        : "string",
  "step"                  : "integer (≥ 0, étape de simulation, 1 step = 1h)",
  "type"                  : "VIREMENT | RETRAIT | DEPOT",
  "amount_xof"            : "float (XOF, > 0)",
  "sender_account_id"     : "string",
  "sender_bank_country"   : "ISO 3166 alpha-2 (ex: SN, CI, ML)",
  "sender_bank_code"      : "string (ex: CBAO, SGBS, ORANGE_SN)",
  "receiver_account_id"   : "string",
  "receiver_bank_country" : "ISO 3166 alpha-2",
  "receiver_bank_code"    : "string",
  "old_balance_sender"    : "float (XOF, solde émetteur avant)",
  "old_balance_receiver"  : "float (XOF, solde récepteur avant)",
  "new_balance_sender"    : "float (XOF, solde émetteur après)",
  "new_balance_receiver"  : "float (XOF, solde récepteur après)",
  "txn_timestamp"         : "string (M/D/YYYY HH:MM ou ISO 8601)",
  "hour_of_day"           : "integer (0-23)",
  "day_of_week"           : "integer (0 = lundi, 6 = dimanche)",
  "channel"               : "mobile_money | cbs | swift (optionnel)"
}
```

## Structure du repo

```
aml-transaction-monitoring/
├── ingestion/          # Kafka producers, consumers, validation
├── feature_engineering/# Calcul des features ML
├── ml/                 # Entraînement, modèles, API scoring
├── alerting/           # Moteur d'alertes
├── frontend/           # Interface compliance React
├── data/synthetic/     # Données de test générées
├── tests/              # Tests unitaires et d'intégration
└── docs/               # Documentation technique
```

## Démarrage rapide

### 1. Cloner et configurer l'environnement

```bash
git clone <repo-url>
cd aml-transaction-monitoring
cp .env.example .env
# Éditer .env avec vos valeurs
```

### 2. Lancer l'infrastructure locale

```bash
docker-compose up -d
```

Services disponibles :
- Kafka UI : http://localhost:8080
- MinIO Console : http://localhost:9001
- MLflow : http://localhost:5000
- Scoring API : http://localhost:8000

### 3. Installer les dépendances Python

```bash
pip install -r requirements.txt
```

### 4. Générer les données synthétiques

```bash
python data/synthetic/generate_mock_data.py
```

### 5. Lancer les tests

```bash
pytest tests/
```

## Conventions

- Branches : `feature/<us-id>-<description>`
- Commits : `feat:`, `fix:`, `docs:`, `test:`, `chore:`
- Variables sensibles → `.env` uniquement
- Chaque module a son `README.md`
