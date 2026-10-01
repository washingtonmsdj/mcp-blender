"""Packaged ORDAX Dev surface with ORDAX account/device pairing."""
from __future__ import annotations

from typing import Any

from ordax_studio.product_auth import ProductAccountError, connect_existing_device

from .desktop import DesktopApi, run_desktop


class ProductDesktopApi(DesktopApi):
    def connect_ordax_account(self, email: str, password: str) -> dict[str, Any]:
        try:
            data = connect_existing_device(
                self.runtime.agent.config,
                str(email or ""),
                str(password or ""),
            )
        except ProductAccountError as error:
            return {
                "ok": False,
                "code": error.code,
                "summary": error.message,
            }
        except Exception as error:
            return {
                "ok": False,
                "code": "ordax_account_unexpected_error",
                "summary": f"{type(error).__name__}: não foi possível conectar a conta ORDAX",
            }
        return {
            "ok": True,
            "summary": "Conta ORDAX conectada a este computador",
            "data": data,
        }

    def ordax_device_status(self) -> dict[str, Any]:
        config = self.runtime.agent.config
        return {
            "ok": True,
            "data": {
                "enrolled": bool(config.device_id),
                "device_id": str(config.device_id or "") or None,
                "control_plane_configured": bool(config.control_plane_url),
            },
        }


def main() -> int:
    return run_desktop(ProductDesktopApi)


if __name__ == "__main__":
    raise SystemExit(main())
