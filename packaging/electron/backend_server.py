#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Electron 内嵌 WebView 的后端服务（HTTP）。

目的：
- 仅启动本地 HTTP 服务（不打开系统浏览器）
- 供 Electron 的 BrowserWindow 直接加载页面与接口
- 在收到 SIGTERM/SIGINT 时优雅停止，避免 Electron 退出后仍在占用端口
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
from http import HTTPStatus
from pathlib import Path
from typing import Optional

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR.parent.parent) not in sys.path:
    # packaging/electron/backend_server.py -> repo root
    sys.path.insert(0, str(THIS_DIR.parent.parent))

import cursor_account_switcher as core  # noqa: E402
import cursor_account_switcher_web as web_app  # noqa: E402


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cursor 账号切换器 Backend (HTTP)")
    p.add_argument("--host", default=web_app.DEFAULT_HOST, help="监听地址（默认: 127.0.0.1）")
    p.add_argument("--port", type=int, default=web_app.DEFAULT_PORT, help="监听端口（默认: 8765）")
    p.add_argument("--db-path", default=str(core.DEFAULT_DB_PATH), help="Cursor state.vscdb 路径")
    p.add_argument("--backup-dir", default=str(core.DEFAULT_BACKUP_DIR), help="快照保存目录")
    return p.parse_args(argv)


def main() -> int:
    args = parse_args()
    db_path = Path(os.path.expanduser(args.db_path)).resolve()
    backup_dir = Path(os.path.expanduser(args.backup_dir)).resolve()

    # 让 Handler 能通过 self.server 访问 db_path/backup_dir
    server = web_app.WebServer(
        (args.host, args.port),
        web_app.Handler,
        db_path=db_path,
        backup_dir=backup_dir,
    )

    # 这行给 Electron 做“启动就绪”轮询用
    url = f"http://{args.host}:{args.port}/"
    print(f"backend_ready {url}", flush=True)

    stop_flag = {"stopping": False}

    def _stop(signum: int, _frame) -> None:
        if stop_flag["stopping"]:
            return
        stop_flag["stopping"] = True
        try:
            server.shutdown()
            server.server_close()
        except Exception:
            # shutdown 在某些情况下可能抛异常；这里吞掉避免阻塞退出
            pass

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    try:
        server.serve_forever()
        return 0
    except KeyboardInterrupt:
        return 0
    except OSError as exc:
        # 端口已占用等错误直接报出，Electron 会感知并重试不同端口
        print(f"backend_error {exc}", file=sys.stderr, flush=True)
        return 1
    except Exception as exc:
        print(f"backend_error {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

