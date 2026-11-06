import socket

import pytest
from cryptography.fernet import Fernet

from app.services import webhook_security


@pytest.fixture
def encryption_key(monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setattr(
        webhook_security.settings,
        "webhook_encryption_key",
        key,
    )
    return key


def public_dns_result(ip="93.184.216.34"):
    return [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            (ip, 443),
        )
    ]


def test_signing_secret_encryption_round_trip(encryption_key):
    secret = webhook_security.generate_signing_secret()

    encrypted = webhook_security.encrypt_signing_secret(secret)

    assert encrypted != secret
    assert webhook_security.decrypt_signing_secret(encrypted) == secret


def test_generated_signing_secrets_are_unique():
    first = webhook_security.generate_signing_secret()
    second = webhook_security.generate_signing_secret()

    assert first != second


def test_encryption_requires_configured_key(monkeypatch):
    monkeypatch.setattr(
        webhook_security.settings,
        "webhook_encryption_key",
        None,
    )

    with pytest.raises(RuntimeError, match="WEBHOOK_ENCRYPTION_KEY"):
        webhook_security.encrypt_signing_secret("test-secret")


def test_encryption_rejects_invalid_key(monkeypatch):
    monkeypatch.setattr(
        webhook_security.settings,
        "webhook_encryption_key",
        "not-a-valid-fernet-key",
    )

    with pytest.raises(RuntimeError, match="invalid"):
        webhook_security.encrypt_signing_secret("test-secret")


def test_decryption_rejects_tampered_ciphertext(encryption_key):
    encrypted = webhook_security.encrypt_signing_secret("test-secret")
    tampered = encrypted[:-2] + "AA"

    with pytest.raises(webhook_security.WebhookSecurityError):
        webhook_security.decrypt_signing_secret(tampered)


def test_encryption_rejects_empty_secret(encryption_key):
    with pytest.raises(webhook_security.WebhookSecurityError):
        webhook_security.encrypt_signing_secret("  ")


def test_valid_public_https_url_is_accepted(monkeypatch):
    monkeypatch.setattr(
        webhook_security.socket,
        "getaddrinfo",
        lambda *args, **kwargs: public_dns_result(),
    )

    url = "https://hooks.example.com/webhooks/supportflow"

    assert webhook_security.validate_webhook_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "http://hooks.example.com/webhook",
        "ftp://hooks.example.com/webhook",
        "https://localhost/webhook",
        "https://127.0.0.1/webhook",
        "https://192.168.1.10/webhook",
        "https://10.0.0.5/webhook",
        "https://[::1]/webhook",
        "https://user:password@hooks.example.com/webhook",
        "https://hooks.example.com/webhook#fragment",
        "https://localhost.localdomain/webhook",
    ],
)
def test_unsafe_webhook_urls_are_rejected(url):
    with pytest.raises(webhook_security.WebhookSecurityError):
        webhook_security.validate_webhook_url(url)


def test_hostname_resolving_to_private_ip_is_rejected(monkeypatch):
    monkeypatch.setattr(
        webhook_security.socket,
        "getaddrinfo",
        lambda *args, **kwargs: public_dns_result("10.0.0.8"),
    )

    with pytest.raises(webhook_security.WebhookSecurityError, match="non-public"):
        webhook_security.validate_webhook_url("https://hooks.example.com/webhook")


def test_hostname_with_mixed_public_and_private_ips_is_rejected(monkeypatch):
    def mixed_dns(*args, **kwargs):
        return public_dns_result() + public_dns_result("192.168.1.5")

    monkeypatch.setattr(webhook_security.socket, "getaddrinfo", mixed_dns)

    with pytest.raises(webhook_security.WebhookSecurityError, match="non-public"):
        webhook_security.validate_webhook_url("https://hooks.example.com/webhook")


def test_unresolvable_hostname_is_rejected(monkeypatch):
    def fail_dns(*args, **kwargs):
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr(webhook_security.socket, "getaddrinfo", fail_dns)

    with pytest.raises(webhook_security.WebhookSecurityError, match="resolved"):
        webhook_security.validate_webhook_url("https://hooks.example.com/webhook")


def test_malformed_url_is_rejected():
    with pytest.raises(webhook_security.WebhookSecurityError):
        webhook_security.validate_webhook_url("https://example.com:invalid/webhook")


def test_url_with_leading_or_trailing_whitespace_is_rejected():
    with pytest.raises(webhook_security.WebhookSecurityError):
        webhook_security.validate_webhook_url(" https://hooks.example.com/webhook ")