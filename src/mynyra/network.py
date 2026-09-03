"""A credential-free TLS check, separate from API/account authentication."""

import socket
import ssl

DEMO_HOST = "demo.ctraderapi.com"
DEMO_PORT = 5035


def check_network(timeout: float = 10) -> dict:
    context = ssl.create_default_context()
    with socket.create_connection((DEMO_HOST, DEMO_PORT), timeout=timeout) as raw:
        with context.wrap_socket(raw, server_hostname=DEMO_HOST) as secure:
            return {
                "proof": "demo_tls",
                "endpoint": f"{DEMO_HOST}:{DEMO_PORT}",
                "tls_version": secure.version(),
                "application_authenticated": False,
                "account_authenticated": False,
            }
