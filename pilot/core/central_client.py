from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pilot.core.bench import Bench


class CentralClientError(Exception):
    """A Central API call could not be made or was rejected (missing config,
    transport failure, or a non-2xx response)."""


def _message(payload: Any) -> Any:
    """Unwrap Frappe's ``{"message": ...}`` envelope that whitelisted methods return,
    tolerating a bare body (e.g. the heartbeat's identity echo)."""
    if isinstance(payload, dict) and "message" in payload:
        return payload["message"]
    return payload


class CentralClient:
    """Calls Central's HTTP API on behalf of this bench's pilot.

    Reads ``central.endpoint`` + ``central.auth_token`` from ``bench.toml`` (written
    by ``bench set-central-config`` at deploy) and authenticates with the
    ``X-Pilot-Token`` header — the reverse of the
    site→bench ``pilot_auth_token`` (PR #133).
    """

    TOKEN_HEADER = "X-Pilot-Token"
    BILLING = "central.billing.api.billing_api"

    def __init__(self, bench: "Bench") -> None:
        self.bench = bench

    def heartbeat(self) -> dict[str, Any]:
        """Prove this pilot can authenticate to Central; returns Central's identity echo
        (team + pilot_credential_id)."""
        return self._get("/api/method/central.api.pilot.heartbeat")

    # --- billing (the credential's team + asset are resolved by Central) ------

    def billing_summary(self) -> dict[str, Any]:
        """Plan, estimate, credit and payment-method state for this bench's asset."""
        return self._billing_get("get_billing_summary")

    def available_plans(self) -> dict[str, Any]:
        """Plans this bench's asset can switch to, flattened + priced for display."""
        return self._billing_get("get_plan_options")

    def change_plan(self, plan: str) -> dict[str, Any]:
        """Switch this bench's asset onto a preset plan."""
        return self._billing_post("change_plan", {"plan": plan})

    def billing_profile(self) -> dict[str, Any]:
        """The team's billing identity + address, with derived setup state."""
        return self._billing_get("get_billing_profile")

    def save_billing_profile(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Create/update the team's billing identity + address."""
        return self._billing_post("save_billing_profile", fields)

    def payment_methods(self) -> list[dict[str, Any]]:
        """The team's saved payment methods (label, brand, last4, default)."""
        return self._billing_get("list_payment_methods")

    def remove_payment_method(self, payment_method: str) -> dict[str, Any]:
        """Remove one of the team's payment methods."""
        return self._billing_post("remove_payment_method", {"payment_method": payment_method})

    def payment_gateways(self) -> list[dict[str, Any]]:
        """The gateways the team can pay through (one per adapter), for the Pay-through choice."""
        return self._billing_get("get_payment_gateways")

    def add_payment_method(self, method_type: str, contact: str | None = None,
                           gateway: str | None = None) -> dict[str, Any]:
        """Begin adding a payment method on the chosen gateway; returns the handles to complete it."""
        return self._billing_post(
            "add_payment_method",
            {"method_type": method_type, "contact": contact, "gateway": gateway},
        )

    def confirm_payment_method(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Finalize the payment method the gateway SDK/checkout tokenised."""
        return self._billing_post("confirm_payment_method", payload)

    def create_payment_method_checkout(self, redirect_url: str, gateway: str | None = None) -> dict[str, Any]:
        """Start adding a card via hosted setup checkout; returns {checkout_url, reference, …}."""
        return self._billing_post("create_payment_method_checkout",
                                  {"redirect_url": redirect_url, "gateway": gateway})

    def confirm_payment_method_checkout(self, reference: str) -> dict[str, Any]:
        """Poll a hosted card setup; on completion stores + validates the card → Active."""
        return self._billing_post("confirm_payment_method_checkout", {"reference": reference})

    def reconcile_payment_setup(self) -> dict[str, Any]:
        """Activate any card whose hosted setup finished while the user was away."""
        return self._billing_post("reconcile_payment_setup", {})

    def create_topup_checkout(self, amount: float, redirect_url: str) -> dict[str, Any]:
        """Start a wallet top-up via hosted checkout; returns {checkout_url, reference, …}."""
        return self._billing_post("create_topup_checkout", {"amount": amount, "redirect_url": redirect_url})

    def checkout_status(self, reference: str) -> dict[str, Any]:
        """Poll a hosted checkout; on first observed paid, credits the wallet idempotently."""
        return self._billing_post("get_checkout_status", {"reference": reference})

    def _billing_get(self, method: str) -> Any:
        return _message(self._get(f"/api/method/{self.BILLING}.{method}"))

    def _billing_post(self, method: str, data: dict[str, Any]) -> Any:
        return _message(self._post(f"/api/method/{self.BILLING}.{method}", data))

    def _credentials(self) -> tuple[str, str]:
        endpoint, token = self._bench_toml_credentials()
        if not (endpoint and token):
            endpoint, token = self._legacy_common_site_config_credentials()
        if not endpoint or not token:
            raise CentralClientError("central.endpoint / central.auth_token not set in bench.toml")
        return endpoint.rstrip("/"), token

    def _bench_toml_credentials(self) -> tuple[str | None, str | None]:
        central = self.bench.config.central
        return central.endpoint, central.auth_token

    def _legacy_common_site_config_credentials(self) -> tuple[str | None, str | None]:
        path = self.bench.sites_path / "common_site_config.json"
        try:
            config = json.loads(path.read_text())
        except (FileNotFoundError, ValueError):
            return None, None
        return config.get("central_endpoint"), config.get("central_auth_token")

    def _get(self, path: str) -> dict[str, Any]:
        return self._request(path, method="GET")

    def _post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        return self._request(path, method="POST", data=data)

    def _request(self, path: str, method: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        endpoint, token = self._credentials()
        headers = {self.TOKEN_HEADER: token}
        body = None
        if data is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(data).encode()
        request = urllib.request.Request(f"{endpoint}{path}", data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            raise CentralClientError(f"Central returned HTTP {exc.code} for {path}") from exc
        except urllib.error.URLError as exc:
            raise CentralClientError(f"Cannot reach Central at {endpoint}: {exc.reason}") from exc
        except ValueError as exc:
            # A 2xx with a non-JSON body (e.g. an HTML error page from a proxy) — decode /
            # json.loads raise ValueError, which the urllib guards above don't cover.
            raise CentralClientError(f"Central returned a non-JSON response for {path}: {exc}") from exc
