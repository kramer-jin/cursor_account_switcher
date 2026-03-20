# cursor_account_switcher

Cursor **多账号**管理工具（**macOS**）：对本机 Cursor 的登录态做**快照备份 / 切换 / 删除快照 / 退出当前账号**，并提供**本地 Web 管理界面**（无需 tkinter）。

仓库：<https://github.com/kramer-jin/cursor_account_switcher>

---

## 环境要求

| 项目 | 说明 |
|------|------|
| 系统 | **macOS**（使用 `osascript` 正常退出 Cursor、`open` 启动 Cursor） |
| Python | **3.9+**（建议 3.10+） |
| Cursor | 已安装，默认数据库路径见下方「数据存储」 |

---

## 仓库里有什么

| 文件 | 用途 |
|------|------|
| `cursor_account_switcher.py` | **命令行**：子命令 `save` / `list` / `current` / `switch` / `delete` / `logout` / `menu` |
| `cursor_account_switcher_web.py` | **本地 Web**：浏览器里完成保存、切换、删除快照、退出账号 |
| `cursor_account_switcher_gui.py` | **Tk 图形界面**（需当前 Python 带 `_tkinter`；Homebrew Python 常无 Tk，可改用 Web 版） |

---

## 快速使用（推荐流程）

1. **先在一个 Cursor 账号下登录好**，在本仓库目录执行：
   ```bash
   python3 cursor_account_switcher.py save work
   ```
2. **在 Cursor 里换另一个账号登录**，再执行：
   ```bash
   python3 cursor_account_switcher.py save personal
   ```
3. **以后切换**（会自动退出 Cursor → 写入新账号登录态 → 尝试再打开 Cursor）：
   ```bash
   python3 cursor_account_switcher.py switch work
   ```

或使用 **Web 界面**（见下文「Web 界面功能说明」）。

---

## 命令行说明（`cursor_account_switcher.py`）

### 全局参数（写在子命令前面）

| 参数 | 说明 |
|------|------|
| `--db-path` | Cursor `state.vscdb` 路径（一般不用改） |
| `--backup-dir` | 快照保存目录，默认 `~/.cursor-account-switcher/accounts` |
| `--force` | Cursor 仍在运行时仍强行读写数据库（**不推荐**，易损坏数据） |
| `--auto-quit` / `--no-auto-quit` | 需要写库前是否自动退出 Cursor（**默认自动退出**） |

示例：

```bash
python3 cursor_account_switcher.py --no-auto-quit current
```

### 子命令

#### `current` — 查看当前登录摘要

```bash
python3 cursor_account_switcher.py current
```

输出当前 `state.vscdb` 里缓存的邮箱、登录方式、会员类型、订阅状态等（只读）。

#### `save <别名>` — 保存当前账号快照

```bash
python3 cursor_account_switcher.py save work
```

将当前 `cursorAuth/*` 写入 `~/.cursor-account-switcher/accounts/work.json`。  
**写入前**若开启 `--auto-quit`（默认），会先尝试退出 Cursor。

#### `list` — 列出已保存快照

```bash
python3 cursor_account_switcher.py list
```

#### `switch <别名>` — 切换到已保存账号

```bash
python3 cursor_account_switcher.py switch work
```

从快照恢复登录态到 `state.vscdb`。  
默认在自动退出 Cursor 后写入，并**尝试** `open -a Cursor` 重新打开（可用 `CURSOR_APP` 指定应用名）。

| 参数 | 说明 |
|------|------|
| `--backup-current 别名` | 切换前先把当前账号再存一份快照（与 Web 里“切换前备份”类似） |
| `--no-restart` | 写入后**不**自动启动 Cursor |

示例：

```bash
python3 cursor_account_switcher.py switch personal --backup-current temp-backup
python3 cursor_account_switcher.py switch work --no-restart
```

#### `delete <别名>` — 删除本地快照文件

```bash
python3 cursor_account_switcher.py delete old_alias
```

只删 `accounts` 目录下对应 json，**不要求**关闭 Cursor，也**不会**改当前 Cursor 登录态。

#### `logout` — 清空当前登录态并关 Cursor

```bash
python3 cursor_account_switcher.py logout
```

删除 `state.vscdb` 中 `cursorAuth/*` 相关项，并按需退出 Cursor（见子命令 `--quit`，默认会尝试关闭）。

#### `menu` — 交互式菜单

```bash
python3 cursor_account_switcher.py menu
```

终端里选择保存 / 切换 / 删除等（切换时会按配置自动退出、备份、重启 Cursor）。

#### 查看帮助

```bash
python3 cursor_account_switcher.py --help
python3 cursor_account_switcher.py switch --help
```

---

## Web 界面（`cursor_account_switcher_web.py`）

### 启动

```bash
python3 cursor_account_switcher_web.py
# 浏览器访问（默认）http://127.0.0.1:8765/
```

常用参数：

| 参数 | 说明 |
|------|------|
| `--host` | 监听地址，默认 `127.0.0.1` |
| `--port` | 端口，默认 `8765` |
| `--open-browser` | 启动后自动打开系统浏览器 |
| `--db-path` / `--backup-dir` | 同 CLI，一般默认即可 |

示例：

```bash
python3 cursor_account_switcher_web.py --open-browser --port 8765
```

首页响应带 `Cache-Control: no-store`，避免浏览器缓存旧页面。

### Web 界面功能说明（页面分区）

| 区域 | 功能 |
|------|------|
| **当前账号** | 展示本机 `state.vscdb` 解析出的当前邮箱、登录方式、会员与订阅摘要；**状态**文案实时反馈操作进度。 |
| **退出账号** | 方形按钮：清空本地 `cursorAuth/*` 并请求关闭 Cursor；完成后会刷新当前账号显示。 |
| **切换账号** | 下拉框选择已保存别名；可勾选「切换前自动退出 Cursor」「切换后自动重新打开 Cursor」「切换前先备份当前账号」。备份别名默认隐藏：若当前邮箱在快照列表里已有对应别名则**不弹窗**；否则切换时会提示输入备份别名。切换完成后 toast 提示是否已尝试重启。 |
| **账号管理** | **保存当前账号**：弹窗输入别名后保存快照并刷新列表。**刷新列表**：重新拉取快照与下拉选项。**已保存账号列表**：展示别名、邮箱、登录方式、会员、保存时间；每条可 **删除**（仅删本地 json，不删 Cursor 里正在用的会话）。 |

本地接口（仅供本页面调用）包括：`/api/current`、`/api/accounts-info`、`/api/save`、`/api/switch`、`/api/delete`、`/api/logout-quit` 等。

---

## Tk 图形界面（可选）

```bash
python3 cursor_account_switcher_gui.py
```

若报错 `No module named '_tkinter'`，说明当前 Python 未带 Tk，请优先使用 **Web 版**，或为系统安装带 Tk 的 Python。

---

## 数据存储与安全

| 数据 | 路径 / 说明 |
|------|-------------|
| Cursor 登录数据库 | `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`（读写 `cursorAuth/*` 等键） |
| 快照文件 | 默认 `~/.cursor-account-switcher/accounts/<别名>.json`，**内含 token** |
| 自定义 Cursor 应用名 | 环境变量 **`CURSOR_APP`**（传给 `open -a`） |

- 请限制 `accounts` 目录权限，勿将快照提交到 Git 或发到不可信渠道。
- 切换账号前**建议**让工具自动退出 Cursor，写完库后再启动，降低数据库竞争风险。

---

## 许可与免责

自用学习交流；二次分发请保留说明。使用本工具修改本机数据的风险由使用者自行承担。
