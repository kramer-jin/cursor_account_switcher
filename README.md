# cursor_account_switcher

Cursor 多账号管理工具（macOS）：备份 / 切换本地登录态、退出当前账号、浏览器管理界面。

仓库地址：<https://github.com/kramer-jin/cursor_account_switcher>

## 环境

- macOS（依赖系统自带 `osascript` / `open`）
- Python 3.9+（推荐 3.10+）

## 文件说明

| 文件 | 说明 |
|------|------|
| `cursor_account_switcher.py` | 命令行：保存、切换、列表、删除、退出账号、交互菜单 |
| `cursor_account_switcher_web.py` | 本地 Web 界面（无需 tkinter） |
| `cursor_account_switcher_gui.py` | Tk 图形界面（需 Python 带 Tk 支持；无 Tk 请用 Web 版） |

## 快速开始

```bash
# 命令行
python3 cursor_account_switcher.py current
python3 cursor_account_switcher.py save mywork
python3 cursor_account_switcher.py switch personal
python3 cursor_account_switcher.py list

# Web（浏览器打开 http://127.0.0.1:8765/）
python3 cursor_account_switcher_web.py --open-browser
```

## 数据与安全

- 登录态来自本机 `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb` 中 `cursorAuth/*`。
- 快照默认保存在 `~/.cursor-account-switcher/accounts/*.json`，含 token，请妥善保管目录权限。
- 切换前会自动退出 Cursor 并可在切换后尝试 `open -a Cursor` 重新打开；可用环境变量 `CURSOR_APP` 指定应用名。

## 许可

按仓库用途自用即可；二次分发请保留说明与风险提示。
