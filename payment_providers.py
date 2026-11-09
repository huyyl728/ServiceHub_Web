"""Payment-provider seam for ServiceHub.

The current product uses an internal demo wallet only. It does not move real money.
Future real payment providers should implement PaymentProvider and verify signed
provider webhooks server-side before marking an external payment as paid.
"""
from dataclasses import dataclass
from typing import Protocol, Mapping, Any

@dataclass(frozen=True)
class PaymentIntent:
    provider: str
    reference: str
    status: str
    checkout_url: str | None = None

class PaymentProvider(Protocol):
    name: str
    def create_payment(self, *, amount_vnd: int, order_reference: str, metadata: Mapping[str, Any]) -> PaymentIntent: ...
    def verify_webhook(self, *, headers: Mapping[str, str], raw_body: bytes) -> Mapping[str, Any]: ...

class DemoWalletProvider:
    """Marker adapter for internal wallet accounting; never represents bank payment."""
    name = "wallet"
    def create_payment(self, *, amount_vnd: int, order_reference: str, metadata: Mapping[str, Any]) -> PaymentIntent:
        if amount_vnd <= 0:
            raise ValueError("amount_vnd must be positive")
        return PaymentIntent(provider=self.name, reference=order_reference, status="internal_wallet_only")
    def verify_webhook(self, *, headers: Mapping[str, str], raw_body: bytes) -> Mapping[str, Any]:
        raise NotImplementedError("Demo wallet has no external webhook. Implement provider-specific signature verification before enabling real payments.")
