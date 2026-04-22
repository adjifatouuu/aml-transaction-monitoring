"""
transaction_consumer.py
-----------------------
Consomme les transactions depuis les topics Kafka AML,
les valide via TransactionValidator, puis les transmet au pipeline
(stockage MinIO Bronze layer).

Topics consommés :
  - aml.transactions.mobile_money
  - aml.transactions.cbs

Comportement :
  - Transactions valides   → publiées dans MinIO bucket "bronze"
  - Transactions invalides → loggées dans data/rejected_transactions.json
"""

import json
import logging
import os
import signal
import sys
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

# Import du validator (chemin relatif au module ingestion)
try:
    from validators.transaction_validator import TransactionValidator
except ModuleNotFoundError:
    # Fallback pour exécution standalone depuis la racine
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from validators.transaction_validator import TransactionValidator

# MinIO (optionnel — désactivé si non configuré)
try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_GROUP_ID          = os.getenv("KAFKA_GROUP_ID", "aml-consumer-group")
KAFKA_TOPICS            = [
    os.getenv("KAFKA_TOPIC_MOBILE_MONEY", "aml.transactions.mobile_money"),
    os.getenv("KAFKA_TOPIC_CBS",          "aml.transactions.cbs"),
]
KAFKA_AUTO_OFFSET_RESET = os.getenv("KAFKA_AUTO_OFFSET_RESET", "earliest")
KAFKA_MAX_POLL_RECORDS  = int(os.getenv("KAFKA_MAX_POLL_RECORDS", "50"))

MINIO_ENDPOINT          = os.getenv("MINIO_ENDPOINT",   "localhost:9000")
MINIO_ACCESS_KEY        = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY        = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET_BRONZE     = os.getenv("MINIO_BUCKET_BRONZE", "bronze")
MINIO_SECURE            = os.getenv("MINIO_SECURE", "false").lower() == "true"

REJECTED_LOG_PATH       = os.getenv("REJECTED_LOG_PATH", "data/rejected_transactions.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("transaction_consumer")


# ---------------------------------------------------------------------------
# Client MinIO
# ---------------------------------------------------------------------------
def _init_minio() -> "Minio | None":
    """Initialise le client MinIO et crée le bucket bronze si nécessaire."""
    if not MINIO_AVAILABLE:
        logger.warning("Package 'minio' non installé. Stockage MinIO désactivé.")
        return None
    try:
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
        )
        if not client.bucket_exists(MINIO_BUCKET_BRONZE):
            client.make_bucket(MINIO_BUCKET_BRONZE)
            logger.info("Bucket MinIO créé : %s", MINIO_BUCKET_BRONZE)
        else:
            logger.info("Bucket MinIO existant : %s", MINIO_BUCKET_BRONZE)
        return client
    except Exception as e:
        logger.warning("MinIO indisponible (%s). Stockage désactivé.", e)
        return None


def _store_in_minio(client: "Minio", transaction: dict, source_topic: str) -> bool:
    """
    Stocke une transaction valide dans MinIO (Bronze layer).

    Chemin objet : bronze/{source}/{date}/{transaction_id}.json
    Ex : bronze/mobile_money/2025-04-22/3fa85f64-....json

    Args:
        client       : Client MinIO initialisé.
        transaction  : Transaction validée.
        source_topic : Topic Kafka d'origine.

    Returns:
        True si stockage réussi, False sinon.
    """
    try:
        # Détermination de la source à partir du topic
        source = "mobile_money" if "mobile_money" in source_topic else "cbs"
        date   = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        txn_id = transaction.get("transaction_id", "unknown")
        object_name = f"{source}/{date}/{txn_id}.json"

        payload = json.dumps(transaction, ensure_ascii=False).encode("utf-8")
        client.put_object(
            bucket_name=MINIO_BUCKET_BRONZE,
            object_name=object_name,
            data=BytesIO(payload),
            length=len(payload),
            content_type="application/json",
        )
        logger.debug("Stocké dans MinIO : %s/%s", MINIO_BUCKET_BRONZE, object_name)
        return True
    except S3Error as e:
        logger.error("Erreur MinIO lors du stockage de %s : %s", txn_id, e)
        return False


# ---------------------------------------------------------------------------
# Consumer principal
# ---------------------------------------------------------------------------
class TransactionConsumer:
    """
    Consumer Kafka multi-topics pour les transactions AML.

    Workflow par message :
      1. Désérialisation JSON
      2. Validation (TransactionValidator)
      3a. Valide   → stockage MinIO Bronze
      3b. Invalide → log dans rejected_transactions.json

    Usage :
        consumer = TransactionConsumer()
        consumer.run()   # boucle infinie
    """

    def __init__(self):
        self._validator = TransactionValidator(rejected_log_path=REJECTED_LOG_PATH)
        self._minio     = _init_minio()
        self._consumer  = None
        self._running   = False

        # Métriques légères
        self._stats = {
            "total":    0,
            "valid":    0,
            "rejected": 0,
            "stored":   0,
        }

        self._connect()
        self._setup_signal_handlers()

    # ------------------------------------------------------------------
    # Connexion Kafka
    # ------------------------------------------------------------------
    def _connect(self) -> None:
        """Initialise le KafkaConsumer sur les topics AML."""
        try:
            self._consumer = KafkaConsumer(
                *KAFKA_TOPICS,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id=KAFKA_GROUP_ID,
                auto_offset_reset=KAFKA_AUTO_OFFSET_RESET,
                enable_auto_commit=False,       # Commit manuel après traitement
                max_poll_records=KAFKA_MAX_POLL_RECORDS,
                value_deserializer=lambda b: json.loads(b.decode("utf-8")),
            )
            logger.info(
                "Consumer Kafka démarré | group=%s | topics=%s",
                KAFKA_GROUP_ID, KAFKA_TOPICS,
            )
        except NoBrokersAvailable:
            logger.error(
                "Impossible de se connecter à Kafka (%s). Arrêt du consumer.",
                KAFKA_BOOTSTRAP_SERVERS,
            )
            sys.exit(1)

    # ------------------------------------------------------------------
    # Gestion des signaux système (arrêt propre)
    # ------------------------------------------------------------------
    def _setup_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT,  self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame) -> None:
        logger.info("Signal %d reçu. Arrêt propre en cours...", signum)
        self._running = False

    # ------------------------------------------------------------------
    # Traitement d'un message
    # ------------------------------------------------------------------
    def _process_message(self, message) -> None:
        """
        Traite un message Kafka individuel.

        Args:
            message : Objet ConsumerRecord Kafka.
        """
        transaction  = message.value
        source_topic = message.topic
        self._stats["total"] += 1

        # Validation
        is_valid, errors = self._validator.validate(transaction)

        if is_valid:
            self._stats["valid"] += 1
            logger.info(
                "[VALID] txn_id=%s | type=%s | amount=%.0f XOF | %s → %s",
                transaction.get("transaction_id", "?"),
                transaction.get("type", "?"),
                transaction.get("amount_xof", 0),
                transaction.get("sender_bank_country", "?"),
                transaction.get("receiver_bank_country", "?"),
            )

            # Stockage MinIO Bronze
            if self._minio:
                stored = _store_in_minio(self._minio, transaction, source_topic)
                if stored:
                    self._stats["stored"] += 1
        else:
            self._stats["rejected"] += 1
            logger.warning(
                "[REJECTED] txn_id=%s | %d erreur(s) : %s",
                transaction.get("transaction_id", "?"),
                len(errors),
                " | ".join(errors),
            )

    # ------------------------------------------------------------------
    # Boucle principale
    # ------------------------------------------------------------------
    def run(self, max_messages: int = 0) -> None:
        """
        Boucle de consommation en continu.

        Args:
            max_messages : Nombre max de messages à traiter (0 = infini).
        """
        self._running = True
        logger.info("Démarrage de la boucle de consommation...")

        try:
            for message in self._consumer:
                if not self._running:
                    break

                self._process_message(message)

                # Commit offset après traitement réussi
                self._consumer.commit()

                # Affichage des stats toutes les 100 transactions
                if self._stats["total"] % 100 == 0:
                    self._log_stats()

                if max_messages and self._stats["total"] >= max_messages:
                    logger.info("Nombre max de messages atteint (%d). Arrêt.", max_messages)
                    break

        except Exception as e:
            logger.error("Erreur inattendue dans la boucle de consommation : %s", e, exc_info=True)
        finally:
            self._shutdown()

    # ------------------------------------------------------------------
    # Stats & arrêt
    # ------------------------------------------------------------------
    def _log_stats(self) -> None:
        s = self._stats
        reject_rate = (s["rejected"] / s["total"] * 100) if s["total"] > 0 else 0
        logger.info(
            "STATS | total=%d | valides=%d | rejetées=%d (%.1f%%) | stockées=%d",
            s["total"], s["valid"], s["rejected"], reject_rate, s["stored"],
        )

    def _shutdown(self) -> None:
        self._log_stats()
        if self._consumer:
            self._consumer.close()
            logger.info("Consumer Kafka fermé proprement.")


# ---------------------------------------------------------------------------
# Entrée principale
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    consumer = TransactionConsumer()
    consumer.run()