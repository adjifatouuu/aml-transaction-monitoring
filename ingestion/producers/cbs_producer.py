"""
cbs_producer.py
---------------
Simule et publie des transactions CBS (Core Banking System) dans un topic Kafka.

Les transactions CBS couvrent les opérations interbancaires UEMOA :
virements SWIFT, transferts interbancaires, opérations de gros montants.

Topic Kafka : aml.transactions.cbs
Mode dégradé : écriture dans data/synthetic/fallback_output.json si Kafka indisponible
"""

import json
import logging
import os
import random
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC             = os.getenv("KAFKA_TOPIC_CBS", "aml.transactions.cbs")
FALLBACK_PATH           = Path("data/synthetic/fallback_output.json")
TRANSACTIONS_PER_BATCH  = int(os.getenv("PRODUCER_BATCH_SIZE", "10"))
INTERVAL_SECONDS        = float(os.getenv("PRODUCER_INTERVAL_SECONDS", "2.0"))
FRAUD_RATE              = float(os.getenv("FRAUD_RATE", "0.05"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("cbs_producer")

# ---------------------------------------------------------------------------
# Données de référence — banques UEMOA agréées BCEAO
# ---------------------------------------------------------------------------
UEMOA_COUNTRIES = ["SN", "CI", "ML", "BF", "TG", "BJ", "NE", "GW"]

# Banques agréées par pays (code BIC simplifié)
BANKS_BY_COUNTRY = {
    "SN": ["CBAO", "SGBS", "BICIS", "BIS", "ATB", "BNDE"],
    "CI": ["SGCI", "BICICI", "NSIA", "BACI", "BOACI", "UBA_CI"],
    "ML": ["BNDA", "BDM", "BSIC_ML", "ORABANK_ML"],
    "BF": ["BCEAO_BF", "SGBB", "BOA_BF", "UBA_BF"],
    "TG": ["UTB", "BTCI", "ORABANK_TG", "BSIC_TG"],
    "BJ": ["BOA_BJ", "SGBBE", "DIAMOND_BJ", "UBA_BJ"],
    "NE": ["BIA_NE", "BOA_NE", "BSIC_NE"],
    "GW": ["BCEAO_GW", "BAO_GW"],
}

# CBS couvre aussi les canaux SWIFT pour les transactions internationales
CBS_CHANNELS = ["cbs", "swift"]

# Profils de montants CBS — typiquement plus élevés que mobile money
AMOUNT_PROFILES = {
    "VIREMENT": (50_000, 500_000_000),    # virements interbancaires importants
    "RETRAIT":  (10_000,  50_000_000),
    "DEPOT":    (10_000, 100_000_000),
}

# Pays hors UEMOA à risque (pour simulation de transactions transfrontalières suspectes)
HIGH_RISK_COUNTRIES = ["NG", "GH", "CM", "GA", "CD", "LY", "DZ"]


# ---------------------------------------------------------------------------
# Générateur de compte bancaire CBS
# ---------------------------------------------------------------------------
def _generate_account_id(country: str, bank_code: str) -> str:
    """Génère un IBAN-like simplifié pour la zone UEMOA."""
    number = random.randint(10_000_000_000, 99_999_999_999)
    return f"{country}{bank_code[:3]}{number}"


# ---------------------------------------------------------------------------
# Générateur de transaction CBS
# ---------------------------------------------------------------------------
def _generate_transaction(step: int, fraud: bool = False) -> dict:
    """
    Génère une transaction CBS synthétique.

    Patterns de fraude CBS simulés :
      - Transactions avec pays à haut risque hors UEMOA
      - Fractionnement : montants juste sous les seuils réglementaires
      - Transactions nocturnes de gros montants (heure_of_day ∈ [0, 4])
      - Solde émetteur insuffisant après transaction

    Args:
        step  : Étape de simulation.
        fraud : Si True, applique un profil suspect.

    Returns:
        dict respectant le contrat transaction_schema.json
    """
    txn_type = random.choice(["VIREMENT", "RETRAIT", "DEPOT"])
    channel  = random.choice(CBS_CHANNELS)

    sender_country = random.choice(UEMOA_COUNTRIES)
    sender_bank    = random.choice(BANKS_BY_COUNTRY.get(sender_country, ["UNKN"]))

    if fraud:
        fraud_pattern = random.choice(["high_risk_country", "structuring", "night_large"])

        if fraud_pattern == "high_risk_country":
            # Transfert vers un pays à risque élevé hors UEMOA
            receiver_country = random.choice(HIGH_RISK_COUNTRIES)
            channel = "swift"
        elif fraud_pattern == "structuring":
            # Fractionnement juste sous le seuil BCEAO (5 000 000 XOF)
            receiver_country = random.choice(UEMOA_COUNTRIES)
        else:
            # Transaction nocturne de gros montant
            receiver_country = random.choice(UEMOA_COUNTRIES)
    else:
        receiver_country = random.choice(UEMOA_COUNTRIES)

    receiver_bank = random.choice(BANKS_BY_COUNTRY.get(receiver_country, ["UNKN"]))

    # Montant
    amount_min, amount_max = AMOUNT_PROFILES[txn_type]
    if fraud:
        if fraud_pattern == "structuring":
            amount = round(random.uniform(4_800_000, 4_999_999), 2)
        elif fraud_pattern == "night_large":
            amount = round(random.uniform(50_000_000, 200_000_000), 2)
        else:
            amount = round(random.uniform(amount_min, amount_max), 2)
    else:
        amount = round(random.uniform(amount_min, amount_max), 2)

    # Soldes
    old_balance_sender   = round(random.uniform(amount * 1.1, amount * 6), 2)
    old_balance_receiver = round(random.uniform(0, 50_000_000), 2)

    if txn_type in ("VIREMENT", "RETRAIT"):
        new_balance_sender   = round(old_balance_sender - amount, 2)
        new_balance_receiver = round(
            old_balance_receiver + (amount if txn_type == "VIREMENT" else 0), 2
        )
    else:  # DEPOT
        new_balance_sender   = old_balance_sender
        new_balance_receiver = round(old_balance_receiver + amount, 2)

    # Timestamp
    if fraud and fraud_pattern == "night_large":
        # Forcer une heure nocturne suspecte
        hour   = random.randint(0, 4)
        days_ago = random.randint(0, 30)
        txn_dt = (
            datetime.now(tz=timezone.utc)
            .replace(hour=hour, minute=random.randint(0, 59), second=0, microsecond=0)
            - timedelta(days=days_ago)
        )
    else:
        txn_dt = datetime.now(tz=timezone.utc) - timedelta(
            days=random.randint(0, 30),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )

    return {
        "transaction_id":        str(uuid.uuid4()),
        "step":                  step,
        "type":                  txn_type,
        "amount_xof":            amount,
        "sender_account_id":     _generate_account_id(sender_country, sender_bank),
        "sender_bank_country":   sender_country,
        "sender_bank_code":      sender_bank,
        "receiver_account_id":   _generate_account_id(receiver_country, receiver_bank),
        "receiver_bank_country": receiver_country,
        "receiver_bank_code":    receiver_bank,
        "old_balance_sender":    old_balance_sender,
        "old_balance_receiver":  old_balance_receiver,
        "new_balance_sender":    new_balance_sender,
        "new_balance_receiver":  new_balance_receiver,
        "txn_timestamp":         txn_dt.strftime("%m/%d/%Y %H:%M"),
        "hour_of_day":           txn_dt.hour,
        "day_of_week":           txn_dt.weekday(),
        "channel":               channel,
    }


# ---------------------------------------------------------------------------
# Sérialisation JSON
# ---------------------------------------------------------------------------
def _json_serializer(data: dict) -> bytes:
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


# ---------------------------------------------------------------------------
# Mode dégradé
# ---------------------------------------------------------------------------
def _write_fallback(transactions: list[dict]) -> None:
    FALLBACK_PATH.parent.mkdir(parents=True, exist_ok=True)

    existing: list[dict] = []
    if FALLBACK_PATH.exists():
        try:
            with open(FALLBACK_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            existing = []

    existing.extend(transactions)

    with open(FALLBACK_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    logger.info("[FALLBACK] %d transaction(s) écrites dans %s", len(transactions), FALLBACK_PATH)


# ---------------------------------------------------------------------------
# Producer principal
# ---------------------------------------------------------------------------
class CBSProducer:
    """
    Producer Kafka pour les transactions CBS.

    Usage :
        producer = CBSProducer()
        producer.run()         # boucle infinie
        producer.send_batch()  # envoi d'un seul batch
    """

    def __init__(self):
        self._step     = 0
        self._producer = None
        self._degraded = False
        self._connect()

    def _connect(self) -> None:
        try:
            self._producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=_json_serializer,
                acks="all",
                retries=3,
                linger_ms=10,
                compression_type="gzip",
            )
            logger.info("Connecté à Kafka : %s | topic : %s", KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC)
            self._degraded = False
        except NoBrokersAvailable:
            logger.warning(
                "Kafka indisponible (%s). Basculement en mode dégradé.",
                KAFKA_BOOTSTRAP_SERVERS,
            )
            self._degraded = True

    def _on_send_success(self, record_metadata) -> None:
        logger.debug(
            "Envoyé → topic=%s | partition=%d | offset=%d",
            record_metadata.topic,
            record_metadata.partition,
            record_metadata.offset,
        )

    def _on_send_error(self, excp) -> None:
        logger.error("Erreur d'envoi Kafka : %s", excp)

    def send_batch(self) -> list[dict]:
        """Génère et envoie un batch de transactions CBS."""
        batch: list[dict] = []

        for _ in range(TRANSACTIONS_PER_BATCH):
            is_fraud = random.random() < FRAUD_RATE
            txn = _generate_transaction(step=self._step, fraud=is_fraud)
            batch.append(txn)
            self._step += 1

        if self._degraded:
            _write_fallback(batch)
        else:
            for txn in batch:
                self._producer.send(KAFKA_TOPIC, value=txn) \
                    .add_callback(self._on_send_success) \
                    .add_errback(self._on_send_error)
            self._producer.flush()
            logger.info("Batch de %d transaction(s) publié sur '%s'", len(batch), KAFKA_TOPIC)

        return batch

    def run(self, max_batches: int = 0) -> None:
        """
        Boucle de production en continu.

        Args:
            max_batches : Nombre max de batches (0 = infini).
        """
        logger.info(
            "Démarrage du producer CBS | batch_size=%d | interval=%.1fs | fraud_rate=%.0f%%",
            TRANSACTIONS_PER_BATCH, INTERVAL_SECONDS, FRAUD_RATE * 100,
        )
        batch_count = 0
        try:
            while True:
                self.send_batch()
                batch_count += 1
                if max_batches and batch_count >= max_batches:
                    logger.info("Nombre max de batches atteint (%d). Arrêt.", max_batches)
                    break
                time.sleep(INTERVAL_SECONDS)
        except KeyboardInterrupt:
            logger.info("Arrêt du producer CBS (KeyboardInterrupt).")
        finally:
            if self._producer:
                self._producer.close()
                logger.info("Connexion Kafka fermée.")

    def close(self) -> None:
        if self._producer:
            self._producer.close()


# ---------------------------------------------------------------------------
# Entrée principale
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    producer = CBSProducer()
    producer.run()