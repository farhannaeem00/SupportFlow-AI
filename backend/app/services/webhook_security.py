import ipaddress
import secrets
import socket
from urllib.parse import urlsplit

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


class WebhookSecurityError(ValueError):
    """Raised when webhook security validation or secret handling fails."""


def _get_fernet() -> Fernet:
    key = settings.webhook_encryption_key

    if not key:
        raise RuntimeError(
            "WEBHOOK_ENCRYPTION_KEY must be configured before "
            "webhook secrets can be stored or retrieved."
        )

    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, TypeError, UnicodeEncodeError) as exc:
        raise RuntimeError(
            "WEBHOOK_ENCRYPTION_KEY is invalid. Generate it with "
            "Fernet.generate_key().decode()."
        ) from exc


def generate_signing_secret() -> str:
    """Generate a cryptographically secure plaintext webhook secret."""
    return secrets.token_urlsafe(32)


def encrypt_signing_secret(secret: str) -> str:
    """Encrypt a plaintext webhook signing secret for database storage."""
    if not secret or not secret.strip():
        raise WebhookSecurityError("Webhook signing secret cannot be empty.")

    encrypted = _get_fernet().encrypt(secret.encode("utf-8"))
    return encrypted.decode("ascii")


def decrypt_signing_secret(encrypted_secret: str) -> str:
    """Decrypt a stored webhook signing secret."""
    if not encrypted_secret:
        raise WebhookSecurityError("Encrypted webhook secret cannot be empty.")

    try:
        decrypted = _get_fernet().decrypt(encrypted_secret.encode("ascii"))
        return decrypted.decode("utf-8")
    except (InvalidToken, ValueError, TypeError, UnicodeEncodeError) as exc:
        raise WebhookSecurityError(
            "Webhook signing secret could not be decrypted."
        ) from exc


def validate_webhook_url(url: str) -> str:
    """
    Validate a public HTTPS webhook destination.

    All DNS answers must be globally routable. Delivery code must repeat
    validation immediately before connecting and prevent redirects; this
    function alone does not eliminate DNS-rebinding/TOCTOU risks.
    """
    if not isinstance(url, str) or not url or len(url) > 2048:
        raise WebhookSecurityError("Webhook URL must be between 1 and 2048 characters.")

    if url != url.strip() or any(ord(char) < 32 or ord(char) == 127 for char in url):
        raise WebhookSecurityError("Webhook URL contains invalid whitespace or control characters.")

    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise WebhookSecurityError("Webhook URL is malformed.") from exc

    if parsed.scheme.lower() != "https":
        raise WebhookSecurityError("Webhook URLs must use HTTPS.")

    if not hostname:
        raise WebhookSecurityError("Webhook URL must include a hostname.")

    if parsed.username is not None or parsed.password is not None:
        raise WebhookSecurityError("Webhook URLs must not contain embedded credentials.")

    if parsed.fragment:
        raise WebhookSecurityError("Webhook URLs must not contain fragments.")

    hostname = hostname.rstrip(".").lower()

    if not hostname or hostname == "localhost" or hostname.endswith(
        (".localhost", ".local", ".internal", ".test", ".invalid", ".example")
    ):
        raise WebhookSecurityError("Local or reserved hostnames are not allowed.")

    effective_port = port or 443

    try:
        ip_address = ipaddress.ip_address(hostname)
    except ValueError:
        # Require a fully qualified hostname; avoid single-label DNS names.
        if "." not in hostname:
            raise WebhookSecurityError("Webhook hostname must be a public domain name.")

        try:
            addresses = socket.getaddrinfo(
                hostname,
                effective_port,
                type=socket.SOCK_STREAM,
            )
        except (socket.gaierror, OSError) as exc:
            raise WebhookSecurityError(
                "Webhook hostname could not be resolved."
            ) from exc

        resolved_ips = {
            result[4][0].split("%", 1)[0]
            for result in addresses
        }

        if not resolved_ips:
            raise WebhookSecurityError("Webhook hostname has no valid IP addresses.")

        for address in resolved_ips:
            try:
                resolved_ip = ipaddress.ip_address(address)
            except ValueError as exc:
                raise WebhookSecurityError(
                    "Webhook hostname resolved to an invalid IP address."
                ) from exc

            if not resolved_ip.is_global:
                raise WebhookSecurityError(
                    "Webhook hostname resolves to a non-public IP address."
                )
    else:
        if not ip_address.is_global:
            raise WebhookSecurityError(
                "Webhook URL must not target a private or reserved IP address."
            )

    return url