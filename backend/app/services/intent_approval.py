
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

from app.models.research_intent import ResearchIntent


class IntentApprovalError(ValueError):
    """Raised when researcher approval is invalid or has expired."""


class IntentApprovalService:
    def __init__(self) -> None:
        configured_secret = os.getenv("BIONEXUS_INTENT_SIGNING_SECRET", "").strip()
        self._secret = (
            configured_secret.encode("utf-8")
            if configured_secret
            else secrets.token_bytes(32)
        )
        self._ttl_seconds = 15 * 60

    @staticmethod
    def _canonical_intent(intent: ResearchIntent) -> bytes:
        payload = intent.model_dump(mode="json")
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    @staticmethod
    def _encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    @staticmethod
    def _decode(value: str) -> bytes:
        try:
            padding = "=" * (-len(value) % 4)
            return base64.urlsafe_b64decode(value + padding)
        except Exception as exc:
            raise IntentApprovalError("Invalid approval token.") from exc

    def issue(self, intent: ResearchIntent) -> str:
        payload: dict[str, Any] = {
            "intent_sha256": hashlib.sha256(
                self._canonical_intent(intent)
            ).hexdigest(),
            "expires_at": int(time.time()) + self._ttl_seconds,
            "nonce": secrets.token_urlsafe(12),
        }
        body = self._encode(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        signature = hmac.new(
            self._secret,
            body.encode("ascii"),
            hashlib.sha256,
        ).digest()
        return f"{body}.{self._encode(signature)}"

    def verify(self, intent: ResearchIntent, token: str) -> None:
        try:
            body, encoded_signature = token.split(".", maxsplit=1)
        except (AttributeError, ValueError) as exc:
            raise IntentApprovalError("Invalid approval token.") from exc

        expected_signature = hmac.new(
            self._secret,
            body.encode("ascii"),
            hashlib.sha256,
        ).digest()
        supplied_signature = self._decode(encoded_signature)

        if not hmac.compare_digest(expected_signature, supplied_signature):
            raise IntentApprovalError("Invalid approval token signature.")

        try:
            payload = json.loads(self._decode(body))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise IntentApprovalError("Invalid approval token payload.") from exc

        if not isinstance(payload, dict):
            raise IntentApprovalError("Invalid approval token payload.")

        if not isinstance(payload.get("expires_at"), int):
            raise IntentApprovalError("Invalid approval token expiry.")

        if payload["expires_at"] <= int(time.time()):
            raise IntentApprovalError("Approval token has expired.")

        expected_hash = hashlib.sha256(self._canonical_intent(intent)).hexdigest()
        approved_hash = payload.get("intent_sha256")

        if not isinstance(approved_hash, str) or not hmac.compare_digest(
            expected_hash, approved_hash
        ):
            raise IntentApprovalError(
                "The research criteria changed after approval. Please review again."
            )


intent_approval_service = IntentApprovalService()
