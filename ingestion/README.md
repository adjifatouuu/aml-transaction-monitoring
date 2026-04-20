# Ingestion

Ce module gère l'entrée des transactions dans le pipeline AML.

## Composants

| Fichier | Rôle |
|---------|------|
| `producers/mobile_money_producer.py` | Publie des transactions Mobile Money dans Kafka |
| `producers/cbs_producer.py` | Publie des transactions CBS dans Kafka |
| `consumers/transaction_consumer.py` | Lit le topic Kafka et transmet au pipeline |
| `validators/transaction_validator.py` | Valide et filtre les transactions entrantes |
| `schemas/transaction_schema.json` | Schéma JSON du contrat de données |

## User Stories couvertes

- **US-11** : Ingestion multi-sources (Mobile Money + CBS) via Kafka
- **US-20** : Validation et nettoyage des données entrantes

## Démarrage

```bash
# Lancer Kafka (via docker-compose depuis la racine)
docker-compose up -d kafka zookeeper

# Producer Mobile Money (simule des transactions en continu)
python ingestion/producers/mobile_money_producer.py

# Consumer
python ingestion/consumers/transaction_consumer.py
```

## Mode dégradé (sans Kafka)

Si Kafka n'est pas disponible, les producers écrivent dans `data/synthetic/fallback_output.json`.

## Règles de validation (US-20)

1. Tous les champs obligatoires présents
2. `amount` > 0
3. `timestamp` valide et non futur
4. `transaction_type` ∈ {virement, retrait, depot}
5. `channel` ∈ {mobile_money, cbs, swift}
6. `sender_country` et `receiver_country` codes ISO 3166 valides
7. `transaction_id` unique (pas de doublon)

Les transactions rejetées sont loggées dans `data/rejected_transactions.json`.
