"""
transaction_validator.py
------------------------
Validation des transactions AML entrantes selon les règles US-20.

Règles appliquées :
  1. Tous les champs obligatoires présents
  2. amount_xof > 0
  3. txn_timestamp valide et non futur
  4. type ∈ {VIREMENT, RETRAIT, DEPOT}
  5. channel ∈ {mobile_money, cbs, swift}  (si présent)
  6. sender_bank_country / receiver_bank_country codes ISO 3166 valides
  7. transaction_id unique (pas de doublon dans la session)
  8. Cohérence des soldes : new_balance_sender = old_balance_sender - amount_xof (VIREMENT/RETRAIT)
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import validate, ValidationError

# ---------------------------------------------------------------------------
# Configuration du logger
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("transaction_validator")

# ---------------------------------------------------------------------------
# Chargement du schéma JSON
# ---------------------------------------------------------------------------
SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "transaction_schema.json"

def _load_schema() -> dict:
    """Charge le schéma JSON depuis le fichier."""
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schéma introuvable : {SCHEMA_PATH}")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

SCHEMA: dict = _load_schema()

# ---------------------------------------------------------------------------
# Formats de timestamp acceptés
# ---------------------------------------------------------------------------
TIMESTAMP_FORMATS = [
    "%m/%d/%Y %H:%M",   # ex : 4/21/2024 14:35
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
]

def _parse_timestamp(value: str) -> datetime | None:
    """Tente de parser le timestamp avec plusieurs formats. Retourne None si échec."""
    for fmt in TIMESTAMP_FORMATS:
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None

# ---------------------------------------------------------------------------
# Classe principale
# ---------------------------------------------------------------------------
class TransactionValidator:
    """
    Valide les transactions AML selon le contrat de données et les règles US-20.

    Usage :
        validator = TransactionValidator()
        is_valid, errors = validator.validate(transaction_dict)
    """

    def __init__(self, rejected_log_path: str = "data/rejected_transactions.json"):
        self._seen_ids: set[str] = set()
        self._rejected_log_path = Path(rejected_log_path)
        self._rejected_log_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Point d'entrée public
    # ------------------------------------------------------------------
    def validate(self, transaction: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Valide une transaction.

        Returns:
            (True, [])             si la transaction est valide.
            (False, [<erreurs>])   sinon, avec la liste des erreurs détectées.
        """
        errors: list[str] = []

        # Règle 1 + types — validation via JSON Schema
        errors.extend(self._validate_schema(transaction))

        # Règle 2 — amount_xof > 0 (déjà dans le schéma mais on double-vérifie)
        errors.extend(self._validate_amount(transaction))

        # Règle 3 — timestamp valide et non futur
        errors.extend(self._validate_timestamp(transaction))

        # Règle 7 — unicité du transaction_id
        errors.extend(self._validate_uniqueness(transaction))

        # Règle 8 — cohérence des soldes
        errors.extend(self._validate_balance_consistency(transaction))

        is_valid = len(errors) == 0

        if not is_valid:
            self._log_rejected(transaction, errors)

        return is_valid, errors

    # ------------------------------------------------------------------
    # Validations internes
    # ------------------------------------------------------------------
    def _validate_schema(self, transaction: dict) -> list[str]:
        """Valide la structure et les types via JSON Schema (règles 1, 4, 5, 6)."""
        try:
            validate(instance=transaction, schema=SCHEMA)
            return []
        except ValidationError as e:
            return [f"Schema error: {e.message}"]

    def _validate_amount(self, transaction: dict) -> list[str]:
        """Règle 2 : amount_xof strictement positif."""
        amount = transaction.get("amount_xof")
        if amount is not None and amount <= 0:
            return [f"amount_xof doit être > 0, reçu : {amount}"]
        return []

    def _validate_timestamp(self, transaction: dict) -> list[str]:
        """Règle 3 : timestamp valide et non dans le futur."""
        raw = transaction.get("txn_timestamp")
        if not raw:
            return ["txn_timestamp est manquant."]

        dt = _parse_timestamp(str(raw))
        if dt is None:
            return [f"txn_timestamp invalide ou format non reconnu : '{raw}'"]

        now = datetime.now(tz=timezone.utc)
        if dt > now:
            return [f"txn_timestamp est dans le futur : '{raw}'"]

        return []

    def _validate_uniqueness(self, transaction: dict) -> list[str]:
        """Règle 7 : transaction_id unique dans la session."""
        txn_id = transaction.get("transaction_id")
        if not txn_id:
            return []  # Déjà capturé par le schema
        if txn_id in self._seen_ids:
            return [f"transaction_id dupliqué : '{txn_id}'"]
        self._seen_ids.add(txn_id)
        return []

    def _validate_balance_consistency(self, transaction: dict) -> list[str]:
        """
        Règle 8 : cohérence des soldes.
        Pour VIREMENT et RETRAIT :
            new_balance_sender ≈ old_balance_sender - amount_xof (tolérance : 1 XOF)
        Pour DEPOT :
            new_balance_receiver ≈ old_balance_receiver + amount_xof
        """
        errors = []
        txn_type = transaction.get("type")
        amount = transaction.get("amount_xof", 0)
        tolerance = 1.0  # 1 XOF

        if txn_type in ("VIREMENT", "RETRAIT"):
            old_s = transaction.get("old_balance_sender")
            new_s = transaction.get("new_balance_sender")
            if old_s is not None and new_s is not None:
                expected = old_s - amount
                if abs(new_s - expected) > tolerance:
                    errors.append(
                        f"Incohérence solde émetteur : "
                        f"old={old_s} - amount={amount} = {expected:.2f}, "
                        f"mais new_balance_sender={new_s}"
                    )

        if txn_type == "DEPOT":
            old_r = transaction.get("old_balance_receiver")
            new_r = transaction.get("new_balance_receiver")
            if old_r is not None and new_r is not None:
                expected = old_r + amount
                if abs(new_r - expected) > tolerance:
                    errors.append(
                        f"Incohérence solde récepteur : "
                        f"old={old_r} + amount={amount} = {expected:.2f}, "
                        f"mais new_balance_receiver={new_r}"
                    )

        return errors

    # ------------------------------------------------------------------
    # Logging des rejets
    # ------------------------------------------------------------------
    def _log_rejected(self, transaction: dict, errors: list[str]) -> None:
        """Persiste les transactions rejetées dans le fichier de log JSON."""
        record = {
            "transaction_id": transaction.get("transaction_id", "UNKNOWN"),
            "rejected_at": datetime.now(tz=timezone.utc).isoformat(),
            "errors": errors,
            "raw": transaction,
        }

        existing: list[dict] = []
        if self._rejected_log_path.exists():
            try:
                with open(self._rejected_log_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, IOError):
                existing = []

        existing.append(record)

        with open(self._rejected_log_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

        logger.warning(
            "Transaction rejetée [%s] — %d erreur(s) : %s",
            record["transaction_id"],
            len(errors),
            "; ".join(errors),
        )


# ---------------------------------------------------------------------------
# Utilisation standalone (tests rapides)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    validator = TransactionValidator()

    # Transaction valide
    valid_txn = {
        "transaction_id": "txn-abc-123",
        "step": 0,
        "type": "VIREMENT",
        "amount_xof": 250000.0,
        "sender_account_id": "SN1234567890",
        "sender_bank_country": "SN",
        "sender_bank_code": "CBAO",
        "receiver_account_id": "CI9876543210",
        "receiver_bank_country": "CI",
        "receiver_bank_code": "NSIA",
        "old_balance_sender": 500000.0,
        "old_balance_receiver": 1200000.0,
        "new_balance_sender": 250000.0,
        "new_balance_receiver": 1450000.0,
        "txn_timestamp": "4/21/2024 14:35",
        "hour_of_day": 14,
        "day_of_week": 0,
    }

    ok, errs = validator.validate(valid_txn)
    print(f"[VALID]  is_valid={ok}, errors={errs}")

    # Transaction invalide (montant négatif + doublon)
    bad_txn = dict(valid_txn, amount_xof=-500.0)
    ok2, errs2 = validator.validate(bad_txn)
    print(f"[INVALID] is_valid={ok2}, errors={errs2}")