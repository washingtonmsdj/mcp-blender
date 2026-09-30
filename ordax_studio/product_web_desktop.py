from __future__ import annotations

from pathlib import Path
from typing import Any

from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig

from .instance_lock import SingleInstanceLock
from .product_auth import ProductAccountError, connect_existing_device
from .web_desktop import APP_NAME, StudioApi


class StudioProductApi(StudioApi):
    """Windows product surface layered over the canonical Studio API.

    The base Studio API remains provider-neutral. Account authentication and
    device ownership live here so development hosts do not need to own or store
    Product credentials.
    """

    def connect_product_account(self, email: str, password: str) -> dict[str, Any]:
        try:
            data = connect_existing_device(self.agent.config, email, password)
        except ProductAccountError as error:
            return {
                "ok": False,
                "code": error.code,
                "summary": error.message,
            }
        except Exception as error:
            return {
                "ok": False,
                "code": "product_account_unexpected_error",
                "summary": f"{type(error).__name__}: não foi possível conectar a conta ORDAX",
            }
        return {
            "ok": True,
            "summary": "Conta ORDAX conectada a este computador",
            "data": data,
        }


def main() -> int:
    try:
        import webview
    except ImportError as error:
        raise SystemExit("pywebview is required for ORDAX Studio WebView shell") from error

    config = AgentConfig.from_env()
    lock = SingleInstanceLock(config.state_dir / "studio-web.lock")
    if not lock.acquire():
        return 0
    try:
        api = StudioProductApi(ActionRegistry(config))
        html = Path(__file__).with_name("studio_product.html").resolve()
        webview.create_window(
            APP_NAME,
            url=html.as_uri(),
            js_api=api,
            width=1600,
            height=960,
            min_size=(1180, 720),
        )
        webview.start(gui="edgechromium", debug=False)
        return 0
    finally:
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
