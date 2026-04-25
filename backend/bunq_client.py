"""bunq client abstraction with fixture and real sandbox implementations."""

from __future__ import annotations

import asyncio
import base64
import copy
import json
import logging
import time
from datetime import date
from pathlib import Path
from typing import Protocol
from uuid import uuid4

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

logger = logging.getLogger(__name__)


class BunqClient(Protocol):
    async def get_transactions(self, monetary_account_id: str | None = None) -> dict: ...
    async def get_buckets(self) -> list[dict]: ...
    async def move_money(self, from_id: str, to_id: str, amount_eur: float) -> str: ...
    async def create_bucket(self, name: str, goal_eur: float) -> dict: ...


class FixtureBunqClient:
    def __init__(self) -> None:
        fixture_path = Path(__file__).parent / "mocks" / "transactions.json"
        with fixture_path.open() as f:
            self._data: dict = copy.deepcopy(json.load(f))

    async def get_transactions(self, monetary_account_id: str | None = None) -> dict:
        if monetary_account_id is not None and monetary_account_id != self._data["monetary_account_id"]:
            return {"monetary_account_id": monetary_account_id, "balance_eur": 0.0, "transactions": []}
        return {
            "monetary_account_id": self._data["monetary_account_id"],
            "balance_eur": self._data["balance_eur"],
            "transactions": self._data["transactions"],
        }

    async def get_buckets(self) -> list[dict]:
        return self._data["buckets"]

    async def move_money(self, from_id: str, to_id: str, amount_eur: float) -> str:
        buckets = self._data["buckets"]
        from_bucket = next((b for b in buckets if b["id"] == from_id), None)
        to_bucket = next((b for b in buckets if b["id"] == to_id), None)

        if from_bucket is None:
            raise ValueError(f"Bucket not found: {from_id}")
        if to_bucket is None:
            raise ValueError(f"Bucket not found: {to_id}")
        if from_bucket["balance_eur"] < amount_eur:
            raise ValueError(f"Insufficient balance in {from_id}: {from_bucket['balance_eur']:.2f} < {amount_eur:.2f}")

        from_bucket["balance_eur"] -= amount_eur
        to_bucket["balance_eur"] += amount_eur

        ref = f"exec_{uuid4().hex[:8]}"
        self._data["transactions"].append({
            "id": ref,
            "date": date.today().isoformat(),
            "amount_eur": -amount_eur,
            "counterparty": to_bucket["name"],
            "description": f"Transfer from {from_bucket['name']} to {to_bucket['name']}",
            "category": "savings",
        })

        return ref

    async def create_bucket(self, name: str, goal_eur: float) -> dict:
        bucket = {
            "id": f"bucket_{uuid4().hex[:8]}",
            "name": name,
            "balance_eur": 0.0,
            "goal_eur": goal_eur,
            "color": "blue",
        }
        self._data["buckets"].append(bucket)
        return bucket


class RealBunqClient:
    """Real bunq sandbox client using the 3-step installation/session flow."""

    def __init__(self, api_key: str, base_url: str, sandbox: bool = True) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._sandbox = sandbox
        self._session_token: str | None = None
        self._bunq_user_id: int | None = None

        # Generate ephemeral RSA key pair for this session
        self._private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self._public_key_pem = self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        self._http = httpx.AsyncClient(timeout=30.0)
        self._session_lock = asyncio.Lock()

    def _sign(self, body: bytes) -> str:
        """RSA-sign the request body and return base64-encoded signature."""
        signature = self._private_key.sign(body, padding.PKCS1v15(), hashes.SHA256())
        return base64.b64encode(signature).decode()

    def _headers(self, token: str | None, body: bytes = b"") -> dict:
        h = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "User-Agent": "bunq-nest/0.1.0",
            "X-Bunq-Language": "en_US",
            "X-Bunq-Region": "en_US",
            "X-Bunq-Geolocation": "0 0 0 0 000",
            "X-Bunq-Client-Request-Id": str(uuid4()),
        }
        if token:
            h["X-Bunq-Client-Authentication"] = token
        if body:
            h["X-Bunq-Client-Signature"] = self._sign(body)
        return h

    @staticmethod
    def _unwrap(response_json: dict) -> dict:
        """Flatten bunq's {Response: [{TypeName: {...}}, ...]} envelope into a single dict."""
        result = {}
        for item in response_json.get("Response", []):
            for key, value in item.items():
                result[key] = value
        return result

    def _check_response(self, resp: httpx.Response, *, label: str = "") -> dict:
        if resp.status_code >= 400:
            try:
                err = resp.json()
                msg = err.get("Error", [{}])[0].get("error_description", resp.text)
            except Exception:
                msg = resp.text
            logger.error(
                "bunq_api_error label=%s status=%d body=%s",
                label, resp.status_code, msg[:500],
            )
            raise ValueError(f"bunq API error {resp.status_code}: {msg}")
        return resp.json()

    async def _ensure_session(self) -> None:
        """Run the 3-step bunq auth flow if no session token is present."""
        if self._session_token:
            return
        async with self._session_lock:
            if self._session_token:
                return

            logger.info("bunq_auth step=installation action=start")
            # Step 1 — Installation (no auth, no signature needed)
            t0 = time.time()
            install_body = json.dumps({"client_public_key": self._public_key_pem}).encode()
            resp = await self._http.post(
                f"{self._base_url}/installation",
                content=install_body,
                headers=self._headers(token=None),
            )
            ms = int((time.time() - t0) * 1000)
            data = self._unwrap(self._check_response(resp, label="installation"))
            installation_token = data["Token"]["token"]
            logger.info("bunq_auth step=installation action=done status=%d latency_ms=%d", resp.status_code, ms)

            # Step 2 — Device Server (signed with our private key)
            t0 = time.time()
            device_body = json.dumps({"description": "bunq Nest backend", "secret": self._api_key}).encode()
            resp = await self._http.post(
                f"{self._base_url}/device-server",
                content=device_body,
                headers=self._headers(token=installation_token, body=device_body),
            )
            ms = int((time.time() - t0) * 1000)
            self._check_response(resp, label="device-server")
            logger.info("bunq_auth step=device_server action=done status=%d latency_ms=%d", resp.status_code, ms)

            # Step 3 — Session Server (signed with our private key)
            t0 = time.time()
            session_body = json.dumps({"secret": self._api_key}).encode()
            resp = await self._http.post(
                f"{self._base_url}/session-server",
                content=session_body,
                headers=self._headers(token=installation_token, body=session_body),
            )
            ms = int((time.time() - t0) * 1000)
            data = self._unwrap(self._check_response(resp, label="session-server"))
            self._session_token = data["Token"]["token"]

            # Extract user ID from whichever user type is present
            for user_type in ("UserPerson", "UserCompany", "UserApiKey"):
                if user_type in data:
                    self._bunq_user_id = data[user_type]["id"]
                    break

            logger.info(
                "bunq_auth step=session_server action=done status=%d latency_ms=%d user_id=%s",
                resp.status_code, ms, self._bunq_user_id,
            )

    async def _get(self, path: str) -> dict:
        logger.info("bunq_request method=GET path=%s", path)
        t0 = time.time()
        resp = await self._http.get(
            f"{self._base_url}{path}",
            headers=self._headers(token=self._session_token),
        )
        if resp.status_code == 401:
            logger.warning("bunq_session_expired method=GET path=%s, re-authenticating", path)
            self._session_token = None
            await self._ensure_session()
            t0 = time.time()
            resp = await self._http.get(
                f"{self._base_url}{path}",
                headers=self._headers(token=self._session_token),
            )
        ms = int((time.time() - t0) * 1000)
        body = self._check_response(resp, label=f"GET {path}")
        logger.info(
            "bunq_response method=GET path=%s status=%d latency_ms=%d body=%s",
            path, resp.status_code, ms, json.dumps(body)[:500],
        )
        return body

    async def _post(self, path: str, body_dict: dict) -> dict:
        logger.info("bunq_request method=POST path=%s", path)
        t0 = time.time()
        body_bytes = json.dumps(body_dict).encode()
        resp = await self._http.post(
            f"{self._base_url}{path}",
            content=body_bytes,
            headers=self._headers(token=self._session_token, body=body_bytes),
        )
        if resp.status_code == 401:
            logger.warning("bunq_session_expired method=POST path=%s, re-authenticating", path)
            self._session_token = None
            await self._ensure_session()
            t0 = time.time()
            resp = await self._http.post(
                f"{self._base_url}{path}",
                content=body_bytes,
                headers=self._headers(token=self._session_token, body=body_bytes),
            )
        ms = int((time.time() - t0) * 1000)
        body = self._check_response(resp, label=f"POST {path}")
        logger.info(
            "bunq_response method=POST path=%s status=%d latency_ms=%d body=%s",
            path, resp.status_code, ms, json.dumps(body)[:500],
        )
        return body

    async def get_transactions(self, monetary_account_id: str | None = None) -> dict:
        await self._ensure_session()
        uid = self._bunq_user_id

        # Find the account to use
        accounts_resp = await self._get(f"/user/{uid}/monetary-account")
        accounts = [list(item.values())[0] for item in accounts_resp.get("Response", [])]

        if monetary_account_id is not None:
            account = next((a for a in accounts if str(a["id"]) == str(monetary_account_id)), None)
        else:
            # Use first active MonetaryAccountBank
            account = next(
                (a for a in accounts if a.get("status") == "ACTIVE"),
                accounts[0] if accounts else None,
            )

        if account is None:
            logger.info("bunq_get_transactions account_id=%s result=no_account", monetary_account_id)
            return {"monetary_account_id": monetary_account_id, "balance_eur": 0.0, "transactions": []}

        account_id = account["id"]
        balance = float(account["balance"]["value"])

        payments_resp = await self._get(
            f"/user/{uid}/monetary-account/{account_id}/payment?count=200"
        )
        payments = [list(item.values())[0] for item in payments_resp.get("Response", [])]

        transactions = [
            {
                "id": str(p["id"]),
                "date": p["created"][:10],
                "amount_eur": float(p["amount"]["value"]),
                "counterparty": p["counterparty_alias"]["display_name"],
                "description": p.get("description", ""),
                "category": "uncategorized",
            }
            for p in payments
        ]

        logger.info(
            "bunq_get_transactions account_id=%s balance_eur=%.2f tx_count=%d",
            account_id, balance, len(transactions),
        )
        return {
            "monetary_account_id": str(account_id),
            "balance_eur": balance,
            "transactions": transactions,
        }

    async def get_buckets(self) -> list[dict]:
        await self._ensure_session()
        uid = self._bunq_user_id

        accounts_resp = await self._get(f"/user/{uid}/monetary-account")
        accounts_raw = accounts_resp.get("Response", [])

        buckets = []
        for item in accounts_raw:
            type_name, account = next(iter(item.items()))
            if account.get("status") not in ("ACTIVE", None):
                continue

            goal_eur = 0.0
            if type_name == "MonetaryAccountSavings":
                sg = account.get("savings_goal")
                if sg:
                    goal_eur = float(sg.get("value", 0.0))

            buckets.append({
                "id": str(account["id"]),
                "name": account.get("description", "Account"),
                "balance_eur": float(account["balance"]["value"]),
                "goal_eur": goal_eur,
                "color": "teal",
            })

        logger.info("bunq_get_buckets bucket_count=%d", len(buckets))
        return buckets

    async def move_money(self, from_id: str, to_id: str, amount_eur: float) -> str:
        await self._ensure_session()
        uid = self._bunq_user_id
        logger.info("bunq_move_money from=%s to=%s amount_eur=%.2f", from_id, to_id, amount_eur)

        # Get destination account details to find its IBAN
        account_resp = await self._get(f"/user/{uid}/monetary-account/{to_id}")
        to_data = self._unwrap(account_resp)
        # _unwrap gives {TypeName: {...}} — grab the first (and only) value
        to_account = next(iter(to_data.values()))
        to_name = to_account.get("description", "Account")

        iban = None
        for alias in to_account.get("alias", []):
            if alias.get("type") == "IBAN":
                iban = alias["value"]
                break

        if iban is None:
            raise ValueError(f"No IBAN alias found for account {to_id}")

        body = {
            "amount": {"value": str(amount_eur), "currency": "EUR"},
            "counterparty_alias": {"type": "IBAN", "value": iban, "name": to_name},
            "description": "Transfer via bunq Nest",
        }
        resp = await self._post(f"/user/{uid}/monetary-account/{from_id}/payment", body)
        data = self._unwrap(resp)
        payment_id = data["Id"]["id"]
        logger.info("bunq_move_money result=ok payment_id=%s", payment_id)
        return f"exec_{payment_id}"

    async def create_bucket(self, name: str, goal_eur: float) -> dict:
        await self._ensure_session()
        uid = self._bunq_user_id
        logger.info("bunq_create_bucket name=%s goal_eur=%.2f", name, goal_eur)

        body = {"currency": "EUR", "description": name}
        resp = await self._post(f"/user/{uid}/monetary-account-bank", body)
        data = self._unwrap(resp)
        account_id = data["Id"]["id"]
        logger.info("bunq_create_bucket result=ok account_id=%s", account_id)

        return {
            "id": str(account_id),
            "name": name,
            "balance_eur": 0.0,
            "goal_eur": goal_eur,
            "color": "teal",
        }


def get_bunq_client() -> BunqClient:
    from backend.config import settings
    if settings.bunq_mode == "fixture":
        return FixtureBunqClient()
    return RealBunqClient(
        api_key=settings.bunq_api_key,
        base_url=settings.bunq_base_url,
        sandbox=settings.bunq_sandbox,
    )
