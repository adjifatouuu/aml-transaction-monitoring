# Data

## Données synthétiques (US-21)

Le script `synthetic/generate_mock_data.py` génère un jeu de 10 000 transactions
réalistes pour bootstrapper le modèle ML V1.

### Génération

```bash
python data/synthetic/generate_mock_data.py
# → data/synthetic/transactions.csv
```

### Structure du fichier généré

| Colonne | Type | Description |
|---------|------|-------------|
| transaction_id | string | UUID unique |
| account_id | string | Compte émetteur (pool de 200 comptes) |
| receiver_id | string | Compte destinataire |
| amount | float | Montant en XOF |
| timestamp | datetime | Date ISO 8601 |
| transaction_type | string | virement / retrait / depot |
| channel | string | mobile_money / cbs / swift |
| sender_country | string | Code ISO 3166 |
| receiver_country | string | Code ISO 3166 |
| label | int | 1 = suspect, 0 = normal (~5% de 1) |

### Distribution attendue

- ~9 500 transactions normales (label=0)
- ~500 transactions suspectes (label=1)

## Données rejetées

`data/rejected_transactions.json` — généré automatiquement par le validateur (US-20).
