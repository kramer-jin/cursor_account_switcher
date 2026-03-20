#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor 账号登录态切换 GUI（macOS / tkinter，无需额外依赖）。

依赖：
- 与 cursor_account_switcher.py 共用同一套读写逻辑
- 读写 Cursor 的本地数据库 state.vscdb 中 cursorAuth/* 字段

运行示例：
python3 /Users/kramer/IdeaProjects/solution/cursor_account_switcher_gui.py
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path
from typing import Optional

import cursor_account_switcher as core


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Cursor 账号切换器")
        self.geometry("650x340")

        self.db_path = core.DEFAULT_DB_PATH
        self.backup_dir = core.DEFAULT_BACKUP_DIR

        self.auto_quit_var = tk.BooleanVar(value=True)
        self.backup_before_switch_var = tk.BooleanVar(value=True)

        self.current_email_var = tk.StringVar(value="(读取中...)")
        self.status_var = tk.StringVar(value="就绪")

        self._build_ui()
        self.refresh_accounts()
        self.refresh_current()

    def _build_ui(self) -> None:
        pad_x = 10
        pad_y = 8

        top = ttk.Frame(self, padding=(pad_x, pad_y))
        top.pack(fill=tk.X)

        ttk.Label(top, text="当前账号:").pack(side=tk.LEFT)
        ttk.Label(top, textvariable=self.current_email_var).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(top, text=" | ").pack(side=tk.LEFT, padx=(10, 10))
        ttk.Checkbutton(top, text="自动退出 Cursor", variable=self.auto_quit_var).pack(side=tk.LEFT)

        mid = ttk.Frame(self, padding=(pad_x, pad_y))
        mid.pack(fill=tk.BOTH, expand=True)

        # 保存
        save_box = ttk.LabelFrame(mid, text="保存当前账号", padding=(pad_x, pad_y))
        save_box.pack(fill=tk.X, pady=(0, 10))

        self.save_name_var = tk.StringVar(value="")
        ttk.Label(save_box, text="别名:").pack(side=tk.LEFT)
        ttk.Entry(save_box, textvariable=self.save_name_var, width=28).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(save_box, text="保存", command=self.on_save_clicked).pack(side=tk.LEFT, padx=(10, 0))

        # 切换/删除
        switch_delete_box = ttk.LabelFrame(mid, text="切换 / 删除账号", padding=(pad_x, pad_y))
        switch_delete_box.pack(fill=tk.BOTH, expand=True)

        # 左：切换
        left = ttk.Frame(switch_delete_box)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.switch_name_var = tk.StringVar(value="")
        ttk.Label(left, text="目标账号:").pack(anchor="w")
        self.account_combo = ttk.Combobox(left, textvariable=self.switch_name_var, state="readonly")
        self.account_combo.pack(fill=tk.X, pady=(6, 10))

        backup_row = ttk.Frame(left)
        backup_row.pack(fill=tk.X)
        ttk.Checkbutton(
            backup_row,
            text="切换前备份当前账号",
            variable=self.backup_before_switch_var,
            command=self._on_backup_checkbox_change,
        ).pack(side=tk.LEFT)
        self.backup_name_var = tk.StringVar(value="backup-temp")
        self.backup_name_entry = ttk.Entry(backup_row, textvariable=self.backup_name_var, width=18)
        self.backup_name_entry.pack(side=tk.LEFT, padx=(8, 0))

        ttk.Button(left, text="切换到选中账号", command=self.on_switch_clicked).pack(fill=tk.X, pady=(0, 10))

        ttk.Button(left, text="刷新账号列表", command=self.refresh_accounts).pack(fill=tk.X)

        # 右：删除
        right = ttk.Frame(switch_delete_box)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(20, 0))

        ttk.Button(right, text="删除选中账号", command=self.on_delete_clicked).pack(fill=tk.X, pady=(0, 10))

        self._status_label = ttk.Label(self, textvariable=self.status_var, anchor="w")
        self._status_label.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=8)

        self._on_backup_checkbox_change()

    def _on_backup_checkbox_change(self) -> None:
        if self.backup_before_switch_var.get():
            self.backup_name_entry.configure(state="normal")
        else:
            self.backup_name_entry.configure(state="disabled")

    def set_status(self, msg: str) -> None:
        self.status_var.set(msg)

    def _run_bg(self, fn, on_success: Optional[str] = None) -> None:
        self.set_status("处理中...")

        def runner() -> None:
            try:
                fn()
                if on_success:
                    self.after(0, lambda: self.set_status(on_success))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("失败", str(exc)))
                self.after(0, lambda: self.set_status("失败"))
            finally:
                self.after(0, self.refresh_current)

        threading.Thread(target=runner, daemon=True).start()

    def _auto_quit_if_needed(self) -> None:
        if self.auto_quit_var.get() and core.is_cursor_running():
            # Tkinter 不是线程安全的：从后台线程只能通过 after() 更新 UI。
            self.after(0, lambda: self.set_status("正在自动退出 Cursor ..."))
            core.quit_cursor()
            if core.is_cursor_running():
                raise RuntimeError("自动退出失败：Cursor 仍在运行。请手动退出后重试。")

    def refresh_accounts(self) -> None:
        names = core.list_account_names(self.backup_dir)
        self.account_combo["values"] = names
        if names and (not self.switch_name_var.get() or self.switch_name_var.get() not in names):
            self.switch_name_var.set(names[0])
        if not names:
            self.switch_name_var.set("")

    def refresh_current(self) -> None:
        try:
            auth_map = core.read_auth_from_db(self.db_path)
            email = auth_map.get("cursorAuth/cachedEmail", "-")
            self.current_email_var.set(str(email))
            self.set_status("就绪")
        except Exception as exc:
            self.current_email_var.set("(读取失败)")
            self.set_status(f"读取当前账号失败: {exc}")

    def on_save_clicked(self) -> None:
        name = self.save_name_var.get().strip()
        if not name:
            messagebox.showwarning("提示", "请输入保存别名（例如 work / personal）。")
            return

        def task() -> None:
            self._auto_quit_if_needed()
            core.save_account(self.backup_dir, self.db_path, name)
            self.after(0, lambda: self.refresh_accounts())

        self._run_bg(task, on_success=f"已保存账号: {name}")

    def on_switch_clicked(self) -> None:
        name = self.switch_name_var.get().strip()
        if not name:
            messagebox.showwarning("提示", "请选择要切换的目标账号。")
            return

        backup_current: Optional[str] = None
        if self.backup_before_switch_var.get():
            backup_current = self.backup_name_var.get().strip() or "backup-temp"

        def task() -> None:
            self._auto_quit_if_needed()
            core.switch_account(self.backup_dir, self.db_path, name, backup_current)

            # 切换后需要重开 Cursor 才会真正生效，这里仅刷新列表与状态提示
            self.after(0, lambda: self.set_status("切换完成：请重启 Cursor 使生效。"))

        self._run_bg(task)

    def on_delete_clicked(self) -> None:
        name = self.switch_name_var.get().strip()
        if not name:
            messagebox.showwarning("提示", "请选择要删除的账号。")
            return

        if not messagebox.askyesno("确认删除", f"确定删除账号别名: {name} ？删除后无法恢复该本地快照。"):
            return

        def task() -> None:
            self._auto_quit_if_needed()
            core.delete_account(self.backup_dir, name)
            self.after(0, lambda: self.refresh_accounts())

        self._run_bg(task, on_success=f"已删除账号: {name}")


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

