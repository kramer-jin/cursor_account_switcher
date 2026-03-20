#!/usr/bin/env python3
"""
Cursor 账号登录态切换工具（macOS）。

功能：
1. 保存当前 Cursor 登录态到本地别名；
2. 从已保存别名切换登录态；
3. 列出、删除、查看当前登录态信息。

注意：
- 切换前请先关闭 Cursor（可用 --force 跳过检查，不推荐）。
- 该工具会读写本机的 Cursor 本地数据库文件。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional


AUTH_KEYS = (
    "cursorAuth/accessToken",
    "cursorAuth/refreshToken",
    "cursorAuth/cachedEmail",
    "cursorAuth/cachedSignUpType",
    "cursorAuth/onboardingDate",
    "cursorAuth/stripeMembershipType",
    "cursorAuth/stripeSubscriptionStatus",
)

DEFAULT_DB_PATH = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Cursor"
    / "User"
    / "globalStorage"
    / "state.vscdb"
)
DEFAULT_BACKUP_DIR = Path.home() / ".cursor-account-switcher" / "accounts"


def is_cursor_running() -> bool:
    """检查 Cursor 是否在运行。"""
    try:
        result = subprocess.run(
            ["pgrep", "-x", "Cursor"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def quit_cursor(wait_seconds: int = 15) -> None:
    """
    让 Cursor 退出（尽力而为）。

    使用 osascript 发起正常退出；如果失败/超时由调用方决定是否需要 --force 继续。
    """
    # 正常退出（不强杀）
    try:
        subprocess.run(
            [
                "osascript",
                "-e",
                'tell application "Cursor" to quit',
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except FileNotFoundError:
        # 没有 osascript（理论上 macOS 一般都有），直接返回，让调用方按情况处理
        return

    # 等待退出完成
    end = time.time() + wait_seconds
    while time.time() < end:
        if not is_cursor_running():
            return
        time.sleep(0.5)


def launch_cursor(app_name: Optional[str] = None, settle_seconds: float = 0.8) -> None:
    """
    启动 Cursor（macOS）。

    使用 `open -a`，应用名默认同环境变量 CURSOR_APP（否则为 Cursor）。
    用于切换账号写入数据库后重新打开，避免“只关不开”。
    """
    name = (app_name or os.environ.get("CURSOR_APP", "Cursor")).strip() or "Cursor"
    try:
        subprocess.run(
            ["open", "-a", name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except FileNotFoundError:
        return
    if settle_seconds > 0:
        time.sleep(settle_seconds)


def ensure_db_exists(db_path: Path) -> None:
    if not db_path.exists():
        raise FileNotFoundError(f"未找到 Cursor 数据库文件: {db_path}")


def read_auth_from_db(db_path: Path) -> Dict[str, str]:
    ensure_db_exists(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in AUTH_KEYS)
        query = f"SELECT key, value FROM ItemTable WHERE key IN ({placeholders})"
        rows = cursor.execute(query, AUTH_KEYS).fetchall()
        data = {key: value for key, value in rows if isinstance(value, str) and value}
        return data
    finally:
        conn.close()


def write_auth_to_db(db_path: Path, auth_map: Dict[str, str]) -> None:
    ensure_db_exists(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        for key in AUTH_KEYS:
            value = auth_map.get(key)
            if value is None:
                continue
            cursor.execute(
                "INSERT OR REPLACE INTO ItemTable(key, value) VALUES (?, ?)",
                (key, value),
            )
        conn.commit()
    finally:
        conn.close()


def logout_current_account(db_path: Path) -> None:
    """
    清空当前 Cursor 账号的本地登录态（等价于“退出账号”）。

    实现方式：删除 state.vscdb 的 cursorAuth/* 相关条目。
    """
    ensure_db_exists(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in AUTH_KEYS)
        cursor.execute(
            f"DELETE FROM ItemTable WHERE key IN ({placeholders})",
            AUTH_KEYS,
        )
        conn.commit()
    finally:
        conn.close()


def backup_file_path(backup_dir: Path, account_name: str) -> Path:
    safe_name = account_name.strip()
    if not safe_name:
        raise ValueError("账号别名不能为空。")
    if "/" in safe_name:
        raise ValueError("账号别名不能包含 '/'.")
    return backup_dir / f"{safe_name}.json"


def save_account(backup_dir: Path, db_path: Path, account_name: str) -> Path:
    auth_map = read_auth_from_db(db_path)
    if "cursorAuth/accessToken" not in auth_map or "cursorAuth/refreshToken" not in auth_map:
        raise RuntimeError("当前未检测到完整登录态（缺少 accessToken/refreshToken）。")

    backup_dir.mkdir(parents=True, exist_ok=True)
    target_file = backup_file_path(backup_dir, account_name)
    payload = {
        "account_name": account_name,
        "saved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "db_path": str(db_path),
        "auth": auth_map,
    }
    target_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target_file


def load_account_payload(backup_dir: Path, account_name: str) -> Dict[str, object]:
    source_file = backup_file_path(backup_dir, account_name)
    if not source_file.exists():
        raise FileNotFoundError(f"账号别名不存在: {account_name}")
    try:
        payload = json.loads(source_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"账号文件格式损坏: {source_file}") from exc

    if not isinstance(payload, dict) or "auth" not in payload:
        raise RuntimeError(f"账号文件缺少 auth 字段: {source_file}")
    if not isinstance(payload["auth"], dict):
        raise RuntimeError(f"账号文件 auth 字段格式错误: {source_file}")
    return payload


def list_accounts(backup_dir: Path) -> None:
    if not backup_dir.exists():
        print("暂无已保存账号。")
        return
    files = sorted(backup_dir.glob("*.json"))
    if not files:
        print("暂无已保存账号。")
        return

    print("已保存账号：")
    for file in files:
        name = file.stem
        saved_at = "-"
        email = "-"
        try:
            payload = json.loads(file.read_text(encoding="utf-8"))
            saved_at = str(payload.get("saved_at", "-"))
            auth = payload.get("auth", {})
            if isinstance(auth, dict):
                email = str(auth.get("cursorAuth/cachedEmail", "-"))
        except Exception:
            pass
        print(f"- {name} | email={email} | saved_at={saved_at}")


def find_saved_account_by_email(backup_dir: Path, email: str) -> Optional[str]:
    """
    在已保存的账号快照中查找相同邮箱的别名（文件名 stem）。
    """
    if not backup_dir.exists():
        return None
    email = (email or "").strip()
    if not email:
        return None

    for file_path in backup_dir.glob("*.json"):
        if not file_path.is_file():
            continue
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            auth = payload.get("auth", {})
            if not isinstance(auth, dict):
                continue
            saved_email = auth.get("cursorAuth/cachedEmail")
            if isinstance(saved_email, str) and saved_email.strip() == email:
                return file_path.stem
        except Exception:
            # 单个文件损坏不影响整体
            continue
    return None


def show_current(db_path: Path) -> None:
    auth_map = read_auth_from_db(db_path)
    email = auth_map.get("cursorAuth/cachedEmail", "-")
    signup = auth_map.get("cursorAuth/cachedSignUpType", "-")
    membership = auth_map.get("cursorAuth/stripeMembershipType", "-")
    status = auth_map.get("cursorAuth/stripeSubscriptionStatus", "-")
    print(f"当前账号: {email}")
    print(f"登录方式: {signup}")
    print(f"会员类型: {membership}")
    print(f"订阅状态: {status}")


def switch_account(
    backup_dir: Path,
    db_path: Path,
    account_name: str,
    auto_backup_current: Optional[str],
) -> Dict[str, Optional[str]]:
    backup_result: Dict[str, Optional[str]] = {
        "backup_skipped": None,
        "existing_name": None,
        "requested_backup_name": auto_backup_current,
    }

    if auto_backup_current:
        # 如果本地已经保存过当前账号，则跳过重复保存（避免重复写入 token 快照）。
        current_auth = read_auth_from_db(db_path)
        current_email = current_auth.get("cursorAuth/cachedEmail", "").strip()
        existing_name = find_saved_account_by_email(backup_dir, current_email)
        if existing_name:
            backup_result["backup_skipped"] = "true"
            backup_result["existing_name"] = existing_name
            print(f"当前账号已保存（别名: {existing_name}），跳过重复备份。")
        else:
            save_account(backup_dir, db_path, auto_backup_current)
            backup_result["backup_skipped"] = "false"
            backup_result["existing_name"] = None
            print(f"已自动备份当前账号为: {auto_backup_current}")

    payload = load_account_payload(backup_dir, account_name)
    auth = payload["auth"]
    assert isinstance(auth, dict)
    auth_map = {str(k): str(v) for k, v in auth.items() if v is not None}
    write_auth_to_db(db_path, auth_map)
    email = auth_map.get("cursorAuth/cachedEmail", "-")
    print(f"已切换到账号别名: {account_name} ({email})")
    print("如未自动重启 Cursor，请手动打开一次以使登录态生效。")
    return backup_result


def delete_account(backup_dir: Path, account_name: str) -> None:
    file_path = backup_file_path(backup_dir, account_name)
    if not file_path.exists():
        raise FileNotFoundError(f"账号别名不存在: {account_name}")
    file_path.unlink()
    print(f"已删除账号别名: {account_name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cursor 账号登录态切换工具")
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help=f"Cursor state.vscdb 路径（默认: {DEFAULT_DB_PATH}）",
    )
    parser.add_argument(
        "--backup-dir",
        default=str(DEFAULT_BACKUP_DIR),
        help=f"账号信息保存目录（默认: {DEFAULT_BACKUP_DIR}）",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="即使检测到 Cursor 正在运行也继续执行（不推荐）",
    )
    parser.add_argument(
        "--auto-quit",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="在需要写入数据库前自动退出 Cursor（默认: 开启）",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    save_parser = subparsers.add_parser("save", help="保存当前登录态")
    save_parser.add_argument("name", help="账号别名，例如: work / personal")

    subparsers.add_parser("list", help="列出已保存账号")
    subparsers.add_parser("current", help="显示当前登录态摘要")

    switch_parser = subparsers.add_parser("switch", help="切换到指定账号")
    switch_parser.add_argument("name", help="目标账号别名")
    switch_parser.add_argument(
        "--backup-current",
        default="",
        help="切换前先备份当前账号到该别名；不传则不备份",
    )
    switch_parser.add_argument(
        "--no-restart",
        action="store_true",
        help="切换写入后不要自动重新启动 Cursor（默认会在已自动退出 Cursor 后尝试重启）",
    )

    subparsers.add_parser(
        "menu",
        help="交互式菜单（保存/切换/查看/删除）",
    )

    delete_parser = subparsers.add_parser("delete", help="删除已保存账号")
    delete_parser.add_argument("name", help="要删除的账号别名")

    logout_parser = subparsers.add_parser("logout", help="退出当前 Cursor 账号并可选关闭 Cursor")
    logout_parser.add_argument(
        "--quit",
        action="store_true",
        default=True,
        help="退出后尝试关闭 Cursor（默认: 开启）",
    )
    return parser.parse_args()


def prompt_str(msg: str, default: Optional[str] = None) -> str:
    if default is None:
        raw = input(msg).strip()
        while not raw:
            raw = input(msg).strip()
        return raw
    raw = input(f"{msg} [{default}]: ").strip()
    return raw if raw else str(default)


def prompt_yes_no(msg: str, default_yes: bool = True) -> bool:
    default_prompt = "Y/n" if default_yes else "y/N"
    raw = input(f"{msg} ({default_prompt}): ").strip().lower()
    if not raw:
        return default_yes
    return raw in {"y", "yes"}


def list_account_names(backup_dir: Path) -> list[str]:
    if not backup_dir.exists():
        return []
    return sorted([p.stem for p in backup_dir.glob("*.json") if p.is_file()])


def interactive_menu(
    backup_dir: Path,
    db_path: Path,
    force: bool,
    auto_quit: bool,
) -> int:
    if not force and is_cursor_running() and auto_quit:
        print("检测到 Cursor 正在运行，正在自动退出 Cursor ...")
        quit_cursor()
        # 仍在运行则交给后续逻辑兜底
        time.sleep(0.2)

    while True:
        print("\n=== Cursor 账号切换菜单 ===")
        # 总是尽量展示“当前账号”信息，但失败不打断菜单
        try:
            show_current(db_path)
        except Exception as exc:
            print(f"(当前账号读取失败: {exc})")

        names = list_account_names(backup_dir)
        print("已保存账号：")
        if not names:
            print("- (none)")
        else:
            for n in names:
                print(f"- {n}")

        print("\n请选择操作：")
        print("1) 保存当前账号")
        print("2) 切换到已保存账号")
        print("3) 删除已保存账号")
        print("4) 退出")

        choice = prompt_str("输入 1-4: ").strip()
        if choice == "1":
            name = prompt_str("请输入账号别名: ")
            try:
                file_path = save_account(backup_dir, db_path, name)
                print(f"已保存账号: {name}")
                print(f"保存文件: {file_path}")
            except Exception as exc:
                print(f"保存失败: {exc}")
        elif choice == "2":
            if not names:
                print("暂无已保存账号，请先用“保存当前账号”。")
                continue
            name = prompt_str("请输入要切换的账号别名（可直接回车跳过筛选）: ")
            backup_current = ""
            if prompt_yes_no("切换前是否备份当前账号？", default_yes=True):
                backup_current = prompt_str("请输入备份别名: ")
            try:
                if not force and auto_quit and is_cursor_running():
                    print("正在自动退出 Cursor ...")
                    quit_cursor()
                switch_account(backup_dir, db_path, name, backup_current or None)
                if auto_quit and not is_cursor_running():
                    print("正在重新启动 Cursor ...")
                    launch_cursor()
            except Exception as exc:
                print(f"切换失败: {exc}")
                continue
            input("按回车键继续...")
        elif choice == "3":
            if not names:
                print("暂无已保存账号。")
                continue
            name = prompt_str("请输入要删除的账号别名: ")
            if not (backup_file_path(backup_dir, name)).exists():
                print("该账号别名不存在。")
                continue
            confirm = input("确认删除将移除本地保存文件。输入 DELETE 以确认: ").strip()
            if confirm != "DELETE":
                print("已取消删除。")
                continue
            try:
                delete_account(backup_dir, name)
            except Exception as exc:
                print(f"删除失败: {exc}")
        elif choice == "4":
            print("再见。")
            return 0
        else:
            print("无效选择，请输入 1-4。")

    return 0


def main() -> int:
    args = parse_args()
    db_path = Path(os.path.expanduser(args.db_path)).resolve()
    backup_dir = Path(os.path.expanduser(args.backup_dir)).resolve()

    if (
        not args.force
        and args.command in {"save", "switch", "menu"}
        and is_cursor_running()
    ):
        if args.auto_quit:
            print("检测到 Cursor 正在运行，正在自动退出 Cursor ...")
            quit_cursor()
            # 再确认一次
            if is_cursor_running():
                print("自动退出失败：Cursor 仍在运行。")
                print("请手动退出 Cursor 后重试，或加 --force 继续（不推荐）。")
                return 2
        else:
            print("检测到 Cursor 正在运行，请先退出 Cursor 后重试。")
            print("如需强制执行可加 --force（可能导致数据不一致）。")
            return 2

    try:
        if args.command == "save":
            file_path = save_account(backup_dir, db_path, args.name)
            print(f"已保存账号: {args.name}")
            print(f"保存文件: {file_path}")
            return 0

        if args.command == "list":
            list_accounts(backup_dir)
            return 0

        if args.command == "current":
            show_current(db_path)
            return 0

        if args.command == "switch":
            backup_name = args.backup_current.strip() if args.backup_current else None
            switch_account(backup_dir, db_path, args.name, backup_name)
            if not args.no_restart and not is_cursor_running():
                print("正在重新启动 Cursor ...")
                launch_cursor()
            return 0

        if args.command == "delete":
            delete_account(backup_dir, args.name)
            return 0

        if args.command == "logout":
            if not args.force and args.quit and is_cursor_running():
                print("检测到 Cursor 正在运行，正在退出 Cursor ...")
                quit_cursor()

            logout_current_account(db_path)
            print("已清空当前账号登录态。")
            if args.quit:
                quit_cursor()
            print("请重新打开 Cursor 后确认已退出。")
            return 0

        if args.command == "menu":
            return interactive_menu(
                backup_dir=backup_dir,
                db_path=db_path,
                force=args.force,
                auto_quit=args.auto_quit,
            )

        print(f"未知命令: {args.command}")
        return 1
    except Exception as exc:
        print(f"执行失败: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
