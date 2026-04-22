# Passation — Ingestion → Feature Engineering

**Projet** : `aml-transaction-monitoring`
**De** : Équipe Ingestion
**Pour** : Équipe Feature Engineering (Spark)
**Date** : 22 avril 2026

---

## 1. Résumé

Le module `ingestion/` est opérationnel. Les transactions Mobile Money et CBS sont validées puis stockées dans **MinIO Bronze** au format JSON. Ce document décrit **où lire les données**, **leur format**, et **la configuration Spark nécessaire** pour les consommer.

---

## 2. Localisation des données dans MinIO

### Connexion

| Paramètre | Valeur (dev local) |
|---|---|
| Endpoint | `http://localhost:9000` |
| Console Web | `http://localhost:9001` |
| Access Key | `minioadmin` (voir `.env`) |
| Secret Key | `minioadmin` (voir `.env`) |
| Path-style access | `true` (obligatoire pour MinIO) |

### Arborescence du bucket `bronze`

```
bronze/
├── mobile_money/
│   ├── 2025-04-22/
│   │   ├── {transaction_id}.json
│   │   ├── {transaction_id}.json
│   │   └── ...
│   └── 2025-04-23/
│       └── ...
└── cbs/
    ├── 2025-04-22/
    │   ├── {transaction_id}.json
    │   └── ...
    └── ...
```

**Convention de nommage** : `bronze/{source}/{YYYY-MM-DD}/{transaction_id}.json`

- `source` ∈ `{mobile_money, cbs}`
- Un fichier = une transaction (1 objet JSON par fichier)
- Partitionnement par date pour faciliter les lectures incrémentales Spark

---

## 3. Contrat de données

Le schéma complet est dans `ingestion/schemas/transaction_schema.json`. Tous les champs listés ci-dessous sont **garantis présents et validés** avant écriture dans Bronze.

### Structure d'une transaction

```json
{
  "transaction_id":        "txn-abc-123",
  "step":                  0,
  "type":                  "VIREMENT",
  "amount_xof":            250000.0,
  "sender_account_id":     "SN1234567890",
  "sender_bank_country":   "SN",
  "sender_bank_code":      "CBAO",
  "receiver_account_id":   "CI9876543210",
  "receiver_bank_country": "CI",
  "receiver_bank_code":    "NSIA",
  "old_balance_sender":    500000.0,
  "old_balance_receiver":  1200000.0,
  "new_balance_sender":    250000.0,
  "new_balance_receiver":  1450000.0,
  "txn_timestamp":         "4/21/2024 14:35",
  "hour_of_day":           14,
  "day_of_week":           0,
  "channel":               "mobile_money"
}
```

### Types et contraintes

| Champ | Type Spark | Contraintes garanties |
|---|---|---|
| `transaction_id` | `StringType` | Unique, non vide |
| `step` | `IntegerType` | ≥ 0 |
| `type` | `StringType` | ∈ {`VIREMENT`, `RETRAIT`, `DEPOT`} |
| `amount_xof` | `DoubleType` | > 0 (strictement positif) |
| `sender_account_id` | `StringType` | Non vide |
| `sender_bank_country` | `StringType` | ISO 3166 alpha-2 (2 lettres majuscules) |
| `sender_bank_code` | `StringType` | Non vide |
| `receiver_account_id` | `StringType` | Non vide |
| `receiver_bank_country` | `StringType` | ISO 3166 alpha-2 |
| `receiver_bank_code` | `StringType` | Non vide |
| `old_balance_sender` | `DoubleType` | ≥ 0 |
| `old_balance_receiver` | `DoubleType` | ≥ 0 |
| `new_balance_sender` | `DoubleType` | ≥ 0 |
| `new_balance_receiver` | `DoubleType` | ≥ 0 |
| `txn_timestamp` | `StringType` | Format `M/D/YYYY HH:MM` ou ISO 8601 |
| `hour_of_day` | `IntegerType` | 0-23 |
| `day_of_week` | `IntegerType` | 0 (lundi) - 6 (dimanche) |
| `channel` | `StringType` | ∈ {`mobile_money`, `cbs`, `swift`} — optionnel |

### Cohérence garantie

Les transactions stockées respectent déjà :
- `amount_xof > 0`
- Soldes cohérents : pour `VIREMENT`/`RETRAIT`, `new_balance_sender ≈ old_balance_sender - amount_xof`
- `txn_timestamp` ≤ timestamp actuel (jamais dans le futur)
- `transaction_id` unique dans une session de production

---

## 4. Configuration Spark pour lire MinIO

### Dépendances requises (jars)

Tu dois inclure ces jars Hadoop dans ton image Spark ou via `--packages` :

```
org.apache.hadoop:hadoop-aws:3.3.4
com.amazonaws:aws-java-sdk-bundle:1.12.262
```

### Exemple SparkSession

```python
from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .appName("aml-feature-engineering")
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin")
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin")
    .config("spark.hadoop.fs.s3a.path.style.access", "true")
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
    .getOrCreate()
)
```

### Endpoint selon le contexte

| Contexte | Endpoint |
|---|---|
| Spark dans Docker Compose (même réseau) | `http://minio:9000` |
| Spark sur la machine hôte | `http://localhost:9000` |
| Production | À définir selon l'infra |

---

## 5. Lecture des données

### Lecture batch (une journée)

```python
df = spark.read.json("s3a://bronze/mobile_money/2025-04-22/")
df.printSchema()
df.show(5)
```

### Lecture de toutes les dates pour une source

```python
df = spark.read.json("s3a://bronze/mobile_money/*/")
```

### Lecture des deux sources unifiées

```python
df_mm  = spark.read.json("s3a://bronze/mobile_money/*/")
df_cbs = spark.read.json("s3a://bronze/cbs/*/")
df     = df_mm.unionByName(df_cbs, allowMissingColumns=True)
```

### Schéma Spark explicite (recommandé pour production)

```python
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, DoubleType
)

transaction_schema = StructType([
    StructField("transaction_id",        StringType(),  False),
    StructField("step",                  IntegerType(), False),
    StructField("type",                  StringType(),  False),
    StructField("amount_xof",            DoubleType(),  False),
    StructField("sender_account_id",     StringType(),  False),
    StructField("sender_bank_country",   StringType(),  False),
    StructField("sender_bank_code",      StringType(),  False),
    StructField("receiver_account_id",   StringType(),  False),
    StructField("receiver_bank_country", StringType(),  False),
    StructField("receiver_bank_code",    StringType(),  False),
    StructField("old_balance_sender",    DoubleType(),  False),
    StructField("old_balance_receiver",  DoubleType(),  False),
    StructField("new_balance_sender",    DoubleType(),  False),
    StructField("new_balance_receiver",  DoubleType(),  False),
    StructField("txn_timestamp",         StringType(),  False),
    StructField("hour_of_day",           IntegerType(), False),
    StructField("day_of_week",           IntegerType(), False),
    StructField("channel",               StringType(),  True),
])

df = (
    spark.read
    .schema(transaction_schema)
    .json("s3a://bronze/mobile_money/2025-04-22/")
)
```

---

## 6. Écriture de la couche Silver

Convention suggérée pour ta sortie :

```
silver/
├── features/
│   ├── date=2025-04-22/
│   │   └── part-*.parquet
│   └── date=2025-04-23/
│       └── part-*.parquet
```

Écriture recommandée en **Parquet partitionné par date** :

```python
(df_features
    .write
    .mode("overwrite")
    .partitionBy("ingestion_date")
    .parquet("s3a://silver/features/")
)
```

---

## 7. Features suggérées (à valider ensemble)

Quelques pistes pour le feature engineering AML :

| Feature | Calcul |
|---|---|
| `amount_to_balance_ratio` | `amount_xof / old_balance_sender` |
| `is_cross_border` | `sender_bank_country != receiver_bank_country` |
| `is_night_transaction` | `hour_of_day ∈ [0, 5]` |
| `is_weekend` | `day_of_week ∈ [5, 6]` |
| `sender_tx_count_1h` | Nb transactions du sender sur la dernière heure (window) |
| `sender_tx_count_24h` | Nb transactions du sender sur 24h |
| `amount_deviation_from_mean` | Écart à la moyenne du sender sur 30j |
| `is_near_threshold` | `amount_xof ∈ [4_800_000, 5_000_000]` (seuil BCEAO) |
| `balance_consistency_check` | `(old_balance_sender - amount_xof - new_balance_sender)` |

---

## 8. Volumétrie attendue

En développement local :
- **~5 transactions/seconde** par producer (configurable via `PRODUCER_INTERVAL_SECONDS`)
- **~5 % de transactions suspectes** (configurable via `FRAUD_RATE`)
- Volume quotidien estimé en dev : ~800 000 transactions/jour si les 2 producers tournent en continu

---

## 9. Contact & points à clarifier

- **Fichiers sources** : `ingestion/` dans le repo
- **Validator utilisé** : `ingestion/validators/transaction_validator.py`
- **Schéma JSON** : `ingestion/schemas/transaction_schema.json`

### Questions ouvertes de mon côté

1. Voulez-vous que j'expose aussi les **transactions rejetées** (`data/rejected_transactions.json`) dans un bucket MinIO dédié pour audit ?
2. Faut-il ajouter un champ `ingestion_timestamp` au moment de l'écriture Bronze pour faciliter le lineage ?
3. Le partitionnement par date actuelle est basé sur **la date de réception** (consumer). Si tu préfères partitionner par `txn_timestamp` (date métier), je peux l'adapter.

---

**Merci de me dire si un point doit être précisé ou si le format ne convient pas à ton pipeline Spark.**
