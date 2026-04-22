"""
mobile_money_producer.py
------------------------
Simule et publie des transactions Mobile Money dans un topic Kafka.

Canaux couverts : Orange Money, Wave, Free Money, MTN MoMo (zone UEMOA)
Topic Kafka     : aml.transactions.mobile_money
Mode dégradé    : écriture dans data/synthetic/fallback_output.json si Kafka indisponible
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
KAFKA_TOPIC              = os.getenv("KAFKA_TOPIC_MOBILE_MONEY", "aml.transactions.mobile_money")
FALLBACK_PATH            = Path("data/synthetic/fallback_output.json")
TRANSACTIONS_PER_BATCH   = int(os.getenv("PRODUCER_BATCH_SIZE", "10"))
INTERVAL_SECONDS         = float(os.getenv("PRODUCER_INTERVAL_SECONDS", "2.0"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("mobile_money_producer")

# ---------------------------------------------------------------------------
# Données de référence UEMOA
# ---------------------------------------------------------------------------
UEMOA_COUNTRIES = ["SN", "CI", "ML", "BF", "TG", "BJ", "NE", "GW"]

MOBILE_MONEY_OPERATORS = {
    "SN": ["ORANGE_SN", "WAVE_SN", "FREE_SN"],
    "CI": ["ORANGE_CI", "MTN_CI", "MOOV_CI"],
    "ML": ["ORANGE_ML", "MOBICASH_ML"],
    "BF": ["ORANGE_BF", "MOOV_BF"],
    "TG": ["TMONEY_TG", "FLOOZ_TG"],
    "BJ": ["MOOV_BJ", "MTN_BJ"],
    "NE": ["AIRTEL_NE", "ZAMANI_NE"],
    "GW": ["ORANGE_GW"],
}

# Profils de montants selon le type de transaction (XOF)
AMOUNT_PROFILES = {
    "VIREMENT": (5_000, 2_000_000),
    "RETRAIT":  (1_000,   500_000),
    "DEPOT":    (1_000, 1_000_000),
}

# Taux de transactions suspectes simulées (pour les tests)
FRAUD_RATE = float(os.getenv("FRAUD_RATE", "0.05"))  # 5 %


# ---------------------------------------------------------------------------
# Générateur de transactions Mobile Money
# ---------------------------------------------------------------------------
def _generate_account_id(country: str) -> str:
    """Génère un identifiant de compte mobile money réaliste."""
    number = random.randint(700_000_000, 799_999_999)
    return f"{country}{number}"


def _generate_transaction(step: int, fraud: bool = False) -> dict:
    """
    Génère une transaction Mobile Money synthétique.

    Args:
        step  : Étape de simulation (entier incrémental).
        fraud : Si True, génère une transaction à profil suspect.

    Returns:
        dict respectant le contrat de données transaction_schema.json
    """
    txn_type      = random.choice(["VIREMENT", "RETRAIT", "DEPOT"])
    sender_country   = random.choice(UEMOA_COUNTRIES)
    receiver_country = random.choice(UEMOA_COUNTRIES)

    amount_min, amount_max = AMOUNT_PROFILES[txn_type]
    if fraud:
        # Montants extrêmes ou juste en dessous du seuil de déclaration BCEAO (500 000 XOF)
        amount = random.choice([
            random.uniform(490_000, 499_999),   # juste sous le seuil
            random.uniform(5_000_000, 20_000_000),  # montant anormalement élevé
        ])
    else:
        amount = round(random.uniform(amount_min, amount_max), 2)

    old_balance_sender   = round(random.uniform(amount, amount * 5), 2)
    old_balance_receiver = round(random.uniform(0, 3_000_000), 2)

    if txn_type in ("VIREMENT", "RETRAIT"):
        new_balance_sender   = round(old_balance_sender - amount, 2)
        new_balance_receiver = round(old_balance_receiver + (amount if txn_type == "VIREMENT" else 0), 2)
    else:  # DEPOT
        new_balance_sender   = old_balance_sender
        new_balance_receiver = round(old_balance_receiver + amount, 2)

    # Timestamp : dans les 30 derniers jours
    txn_dt = datetime.now(tz=timezone.utc) - timedelta(
        days=random.randint(0, 30),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )

    sender_bank_code = random.choice(
        MOBILE_MONEY_OPERATORS.get(sender_country, ["UNKNOWN"])
    )

    return {
        "transaction_id":      str(uuid.uuid4()),
        "step":                step,
        "type":                txn_type,
        "amount_xof":          amount,
        "sender_account_id":   _generate_account_id(sender_country),
        "sender_bank_country": sender_country,
        "sender_bank_code":    sender_bank_code,
        "receiver_account_id": _generate_account_id(receiver_country),
        "receiver_bank_country": receiver_country,
        "receiver_bank_code":  random.choice(
            MOBILE_MONEY_OPERATORS.get(receiver_country, ["UNKNOWN"])
        ),
        "old_balance_sender":    old_balance_sender,
        "old_balance_receiver":  old_balance_receiver,
        "new_balance_sender":    new_balance_sender,
        "new_balance_receiver":  new_balance_receiver,
        "txn_timestamp":         txn_dt.strftime("%m/%d/%Y %H:%M"),
        "hour_of_day":           txn_dt.hour,
        "day_of_week":           txn_dt.weekday(),
        "channel":               "mobile_money",
        # Metadata interne (non inclus dans le schéma strict — à retirer si additionalProperties=false)
        # "_is_fraud_sim": fraud,
    }


# ---------------------------------------------------------------------------
# Sérialisation JSON pour Kafka
# ---------------------------------------------------------------------------
def _json_serializer(data: dict) -> bytes:
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


# ---------------------------------------------------------------------------
# Mode dégradé — écriture fichier
# ---------------------------------------------------------------------------
def _write_fallback(transactions: list[dict]) -> None:
    """Écrit les transactions dans le fichier fallback si Kafka est indisponible."""
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
class MobileMoneyProducer:
    """
    Producer Kafka pour les transactions Mobile Money.

    Usage :
        producer = MobileMoneyProducer()
        producer.run()        # boucle infinie
        producer.send_batch() # envoi d'un seul batch
    """

    def __init__(self):
        self._step      = 0
        self._producer  = None
        self._degraded  = False
        self._connect()

    def _connect(self) -> None:
        """Tente de se connecter à Kafka. Bascule en mode dégradé si échec."""
        try:
            self._producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=_json_serializer,
                acks="all",               # Attendre confirmation de tous les replicas
                retries=3,
                linger_ms=10,             # Légère attente pour le batching
                compression_type="gzip",
            )
            logger.info("Connecté à Kafka : %s | topic : %s", KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC)
            self._degraded = False
        except NoBrokersAvailable:
            logger.warning(
                "Kafka indisponible (%s). Basculement en mode dégradé (fichier).",
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
        """
        Génère et envoie un batch de transactions.

        Returns:
            Liste des transactions générées dans ce batch.
        """
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
            "Démarrage du producer Mobile Money | batch_size=%d | interval=%.1fs | fraud_rate=%.0f%%",
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
            logger.info("Arrêt du producer (KeyboardInterrupt).")
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
    producer = MobileMoneyProducer()
    producer.run(max_batches=2)