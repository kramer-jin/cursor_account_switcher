#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
macOS .app 入口：启动本地 Web 服务并打开浏览器。

开发运行（在项目根目录，与 cursor_account_switcher*.py 同级）：
  python3 packaging/macos/launcher.py

打包后由 PyInstaller 解压到 sys._MEIPASS，内含同目录的 core / web 脚本。
"""
from __future__ import annotations

import os
import socket
import sys
from pathlib import Path


def _bundle_root() -> Path:
    """运行目录：打包后为 _MEIPASS；开发时为 IdeaProjects/solution。"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    # packaging/macos/launcher.py -> solution
    return Path(__file__).resolve().parent.parent.parent


def _is_port_listening(host: str, port: int, timeout_sec: float = 0.25) -> bool:
    """快速判断端口是否已被占用。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout_sec)
        return s.connect_ex((host, port)) == 0


def main() -> int:
    root = _bundle_root()
    sys.path.insert(0, str(root))
    os.chdir(root)

    host = os.environ.get("CURSOR_ACCOUNT_SWITCHER_HOST", "127.0.0.1").strip()
    base_port = int(os.environ.get("CURSOR_ACCOUNT_SWITCHER_PORT", "8765").strip())
    candidate_ports = [base_port] + [base_port + i for i in range(1, 20)]

    argv_bak = sys.argv[:]
    try:
        import cursor_account_switcher_web as web_app  # noqa: WPS433
        import webbrowser  # noqa: WPS433

        # 避免二次打开导致的端口冲突：端口已在监听时，直接打开现有页面。
        if _is_port_listening(host, base_port):
            webbrowser.open(f"http://{host}:{base_port}/")
            return 0

        # 端口冲突时依次尝试其他端口，避免“闪退”。
        last_exc: OSError | None = None
        for port in candidate_ports:
            try:
                sys.argv = [
                    "cursor_account_switcher_web",
                    "--host",
                    host,
                    "--port",
                    str(port),
                    "--open-browser",
                ]
                return int(web_app.main())
            except OSError as exc:
                last_exc = exc
                if getattr(exc, "errno", None) != 48:  # Errno 48: Address already in use
                    raise
                continue

        if last_exc is not None:
            raise last_exc
        return 1
    finally:
        sys.argv = argv_bak


if __name__ == "__main__":
    raise SystemExit(main())

