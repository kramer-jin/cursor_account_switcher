#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor 账号登录态切换 Web 界面（无 tkinter 依赖，macOS 可用）。

特点：
- 使用 Python 标准库 `http.server`；
- 浏览器访问 `http://127.0.0.1:8765/` 即可保存/切换/删除；
- 写入 Cursor 本地数据库前可选自动退出 Cursor。
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

import cursor_account_switcher as core  # noqa: E402


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


HTML = r"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Cursor 账号切换器</title>
    <style>
      :root{
        --bg0:#f6f7fb;
        --bg1:#ffffff;
        --text:#0f172a;
        --muted:#64748b;
        --border: rgba(15, 23, 42, .12);
        --shadow: 0 16px 40px rgba(15, 23, 42, .10);
        --primary:#3b82f6;
        --primary2:#2563eb;
        --danger:#ef4444;
        --danger2:#e11d48;
        --card:#ffffff;
        --chip:#f1f5ff;
      }

      body{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial;
        margin:0;
        padding: 22px 16px 30px;
        min-height: 100vh;
        color: var(--text);
        background:
          radial-gradient(900px circle at 10% -10%, rgba(59,130,246,.18), transparent 55%),
          radial-gradient(700px circle at 90% 0%, rgba(99,102,241,.12), transparent 55%),
          linear-gradient(180deg, var(--bg0), var(--bg1));
      }

      .container{
        max-width: 1120px;
        margin: 0 auto;
      }

      h2{
        font-size: 20px;
        margin: 0 0 16px 0;
        font-weight: 800;
        letter-spacing: .2px;
      }

      h3{
        font-size: 15px;
        margin: 0 0 10px 0;
        font-weight: 950;
        letter-spacing: .2px;
      }

      .row { display: flex; gap: 14px; flex-wrap: wrap; align-items: flex-start; }

      .layout-grid{
        display: grid;
        grid-template-columns: 1fr 1fr;
        grid-template-areas:
          "status switch"
          "manage manage";
        gap: 14px;
        align-items: stretch;
        margin-top: 12px;
      }

      .status-card{
        grid-area: status;
        display: flex;
        flex-direction: column;
      }

      .left-col{
        grid-area: manage;
        display: flex;
        flex-direction: column;
        gap: 14px;
        align-items: stretch;
      }

      .right-col{
        grid-area: switch;
        display: flex;
        flex-direction: column;
        align-items: stretch;
      }

      .status-card{
        height: 100%;
      }

      .right-col{
        height: 100%;
      }

      .switch-card{
        flex: 1;
        min-height: 0;
      }

      .logout-row{
        margin-top: auto;
        justify-content: flex-end !important;
      }

      .card{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 16px 16px 14px;
        min-width: 0;
        box-shadow: var(--shadow);
      }

      .left-col .card,
      .right-col .card{
        width: 100%;
      }

      label { display: inline-block; min-width: 84px; font-weight: 650; color: var(--text); }

      input, select, button{
        padding: 8px 10px;
        border-radius: 10px;
        border: 1px solid var(--border);
        background: #fff;
        color: var(--text);
      }

      input:focus, select:focus{
        outline: none;
        border-color: rgba(37, 99, 235, .55);
        box-shadow: 0 0 0 3px rgba(37, 99, 235, .12);
      }

      button{
        cursor: pointer;
        padding: 9px 14px;
        border: none;
        font-weight: 750;
        background: linear-gradient(180deg, var(--primary), var(--primary2));
        color: #fff;
        transition: transform .12s ease, filter .12s ease;
      }
      button:hover{ filter: brightness(1.03); transform: translateY(-1px); }
      button:active{ transform: translateY(0); }

      .btn-danger{
        background: linear-gradient(180deg, var(--danger), var(--danger2));
      }

      .btn-secondary{
        background: linear-gradient(180deg, #e5e7eb, #cbd5e1);
        color: #0f172a;
      }

      .square-btn{
        width: 52px;
        height: 52px;
        padding: 0;
        border-radius: 16px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 950;
        font-size: 12px;
        box-shadow: 0 10px 24px rgba(37, 99, 235, .18);
      }

      input[type="checkbox"]{
        margin: 0;
        transform: translateY(1px);
      }

      .status{
        margin-top: 12px;
        color: var(--muted);
        font-weight: 650;
      }
      #status{
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        background: var(--chip);
        color: var(--text);
        font-weight: 800;
        margin-left: 6px;
      }

      .small { color: var(--muted); font-size: 12px; margin-top: 6px; }

      .kv { line-height: 1.75; }
      .kv b { display: inline-block; min-width: 104px; color: var(--muted); font-weight: 700; }

      .toast{
        color: #111;
        background: #f3f7ff;
        border: 1px solid #d8e2ff;
        padding: 10px 12px;
        border-radius: 10px;
        margin-top: 12px;
        display: none;
        font-weight: 650;
      }

      .acc-info{
        margin-top: 12px;
        border: 1px solid rgba(15, 23, 42, .08);
        border-radius: 12px;
        padding: 10px 12px;
        background: linear-gradient(180deg, #fff, #fafbff);
        max-height: 180px;
        overflow: auto;
      }

      .acc-item{
        padding: 12px 12px;
        border: 1px solid rgba(15, 23, 42, .08);
        border-radius: 12px;
        margin: 0 0 10px 0;
        background: rgba(255, 255, 255, .92);
      }
      .acc-item:last-child{ margin-bottom: 0; }

      .acc-item .name{
        font-weight: 900;
        letter-spacing: .2px;
      }
      .acc-item .meta{
        margin-top: 4px;
        color: var(--muted);
        font-size: 12px;
        line-height: 1.45;
      }

      .acc-item .actions{
        flex: 0 0 auto;
      }

      .acc-item .item-row{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
      }

      .btn-danger-sm{
        background: linear-gradient(180deg, var(--danger), var(--danger2));
        padding: 7px 10px;
        border-radius: 10px;
        font-size: 13px;
        font-weight: 900;
        box-shadow: 0 10px 24px rgba(225, 29, 72, .16);
      }

      .btn-danger-sm:hover{ filter: brightness(1.03); transform: translateY(-1px); }
      .btn-danger-sm:active{ transform: translateY(0); }

      .section-title{
        font-size: 15px;
        margin: 0 0 10px 0;
        font-weight: 900;
      }

      @media (max-width: 920px){
        .layout-grid{ grid-template-columns: 1fr; }
        .layout-grid{ grid-template-areas: "status" "switch" "manage"; }
        .status-card{ grid-area: auto; }
        .left-col{ grid-area: auto; }
        .right-col{ grid-area: auto; }
        .card{ min-width: 100%; }
      }

      @media (prefers-reduced-motion: reduce){
        button{ transition:none; }
        button:hover{ transform:none; }
      }
    </style>
  </head>
  <body>
    <div class="container">
    <h2>Cursor 账号切换器</h2>

    <div class="layout-grid">
      <div class="card status-card">
        <div class="kv">
          <div><b>当前账号邮箱：</b><span id="curEmail">-</span></div>
          <div><b>登录方式：</b><span id="curSignup">-</span></div>
          <div><b>会员类型：</b><span id="curMembership">-</span></div>
          <div><b>订阅状态：</b><span id="curStatus">-</span></div>
        </div>
        <div class="small">切换完成后请重启 Cursor 才会完全生效。</div>
        <div class="status">状态：<span id="status">就绪</span></div>
        <div class="toast" id="toast"></div>

        <div class="row logout-row" style="margin-top: 10px; justify-content: flex-end;">
          <button
            class="btn-secondary square-btn"
            onclick="logoutAndQuit()"
            title="退出当前账号（清空本地登录态）并关闭 Cursor"
          >退出账号</button>
        </div>
      </div>

      <div class="left-col">
        <div class="card manage-card">
          <h3 style="margin: 0 0 10px 0;">账号管理</h3>
          <div class="small">保存/删除的是本地账号快照，不影响 Cursor 当前登录态之外的账号。</div>

          <div class="row" style="margin-top: 12px;">
            <button onclick="saveCurrent()">保存当前账号</button>
            <button onclick="refreshAll()" class="btn-secondary" style="margin-left: 10px;">刷新列表</button>
          </div>

          <div class="small" style="margin-top: 8px;">保存的是本地登录态快照（token），请注意隐私与安全。</div>

          <div style="margin-top: 12px; font-weight: 900;">已保存账号（删除快照）</div>
          <div id="accountsManage" class="acc-info small"></div>
        </div>
      </div>

      <div class="right-col">
        <div class="card switch-card">
          <h3 style="margin: 0 0 10px 0;">切换账号</h3>
          <div class="row">
            <label>账号</label>
            <select id="selName" style="min-width: 220px;"></select>
          </div>

          <div class="row" style="margin-top: 10px;">
            <input type="checkbox" id="autoQuit" checked />
            <label for="autoQuit" style="min-width: auto;">切换前自动退出 Cursor</label>
          </div>

          <div class="row" style="margin-top: 10px;">
            <input type="checkbox" id="restartAfter" checked />
            <label for="restartAfter" style="min-width: auto;">切换后自动重新打开 Cursor</label>
          </div>

          <div class="row" style="margin-top: 10px;">
            <input type="checkbox" id="backupBefore" checked />
            <label for="backupBefore" style="min-width: auto;">切换前先备份当前账号</label>
          </div>

        <div id="backupNameRow" class="row" style="margin-top: 10px; opacity: 1; display:none;">
          <label>备份别名</label>
          <input id="backupName" value="" style="min-width: 220px;" />
        </div>

          <div class="row" style="margin-top: 10px;">
            <button onclick="switchAccount()">切换</button>
          </div>
        </div>
      </div>
    </div>
  </div>

    <script>
      const $ = (id) => document.getElementById(id);
      function setStatus(msg){ $("status").textContent = msg; }
      function toast(msg){
        const el = $("toast");
        el.style.display = "block";
        el.textContent = msg;
        setTimeout(()=>{ el.style.display="none"; }, 2500);
      }

      async function apiGet(path){
        const res = await fetch(path, { method: "GET" });
        const data = await res.json().catch(()=>({}));
        if(!res.ok){ throw new Error(data && data.error ? data.error : ("HTTP " + res.status)); }
        return data;
      }

      async function apiPost(path, body){
        const res = await fetch(path, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body || {})
        });
        const data = await res.json().catch(()=>({}));
        if(!res.ok){ throw new Error(data && data.error ? data.error : ("HTTP " + res.status)); }
        return data;
      }

      function gatherBackup(){
        if(!$("backupBefore").checked) return { enabled: false, name: "" };
        // 备份别名输入框是隐藏的：这里先不填 name，由 switchAccount() 根据当前账号是否已存在别名来自动补全
        return { enabled: true, name: "" };
      }

      async function refreshAll(){
        setStatus("刷新中...");
        const cur = await apiGet("/api/current");
        $("curEmail").textContent = cur.email || "-";
        $("curSignup").textContent = cur.signup || "-";
        $("curMembership").textContent = cur.membership || "-";
        $("curStatus").textContent = cur.status || "-";

        const infos = await apiGet("/api/accounts-info");
        const sel = $("selName");
        sel.innerHTML = "";
        const manageEl = $("accountsManage");
        manageEl.innerHTML = "";

        if(!infos || infos.length === 0){
          const opt = document.createElement("option");
          opt.value = "";
          opt.textContent = "(none)";
          sel.appendChild(opt);
          manageEl.innerHTML = "暂无已保存账号。";
          setStatus("就绪");
          return;
        }

        infos.forEach(acc => {
          const opt = document.createElement("option");
          opt.value = acc.name;
          opt.textContent = acc.email ? `${acc.name} | ${acc.email}` : acc.name;
          sel.appendChild(opt);

          const item = document.createElement("div");
          item.className = "acc-item";

          const row = document.createElement("div");
          row.className = "item-row";

          const left = document.createElement("div");
          const nameEl = document.createElement("div");
          nameEl.className = "name";
          nameEl.textContent = acc.name;

          const savedAt = acc.saved_at ? acc.saved_at : "-";
          const meta = [];
          if(acc.email) meta.push("email: " + acc.email);
          if(acc.signup) meta.push("登录方式: " + acc.signup);
          if(acc.membership) meta.push("会员类型: " + acc.membership);
          meta.push("保存时间: " + savedAt);

          const metaEl = document.createElement("div");
          metaEl.className = "meta";
          metaEl.textContent = meta.join(" | ");

          left.appendChild(nameEl);
          left.appendChild(metaEl);

          const actions = document.createElement("div");
          actions.className = "actions";

          const delBtn = document.createElement("button");
          delBtn.className = "btn-danger-sm";
          delBtn.textContent = "删除";
          delBtn.addEventListener("click", () => deleteAccountByName(acc.name));

          actions.appendChild(delBtn);
          row.appendChild(left);
          row.appendChild(actions);
          item.appendChild(row);
          manageEl.appendChild(item);
        });

        setStatus("就绪");
        // 强制等高：CSS 有时受内容/渲染影响不如预期，这里动态对齐两张顶栏卡片高度
        setTimeout(syncTopCards, 0);
      }

      function syncTopCards(){
        try{
          const mq = window.matchMedia && window.matchMedia("(max-width: 920px)");
          if(mq && mq.matches){
            // 移动端上下堆叠，不强制等高
            const a = document.querySelector(".status-card");
            const b = document.querySelector(".switch-card");
            if(a) a.style.height = "auto";
            if(b) b.style.height = "auto";
            return;
          }

          const a = document.querySelector(".status-card");
          const b = document.querySelector(".switch-card");
          if(!a || !b) return;

          a.style.height = "auto";
          b.style.height = "auto";
          const ha = a.getBoundingClientRect().height;
          const hb = b.getBoundingClientRect().height;
          const h = Math.max(ha, hb);
          a.style.height = h + "px";
          b.style.height = h + "px";
        }catch(e){
          // 不影响主功能
        }
      }

      async function saveCurrent(){
        const input = window.prompt("请输入保存别名（例如 work / personal）：", "");
        const name = (input || "").toString().trim();
        if(!name){ toast("已取消或别名为空"); return; }
        setStatus("保存中...");
        await apiPost("/api/save", { name });
        toast("已保存账号: " + name);
        await refreshAll();
      }

      async function switchAccount(){
        const name = $("selName").value;
        if(!name){ toast("请选择要切换的账号"); return; }
        const backup = gatherBackup();
        const autoQuit = $("autoQuit").checked;
        // 未退出 Cursor 时不应自动再开一份实例
        const restartAfter =
          autoQuit && ($("restartAfter") ? $("restartAfter").checked : true);

        // 切换前备份：优先判断“当前账号是否已经有别名”
        // 如果已有别名：直接复用该别名，不弹窗
        // 如果没有别名：才弹窗让你输入备份别名
        if(backup && backup.enabled){
          const cur = await apiGet("/api/current");
          const curEmail = (cur.email || "").toString().trim();
          const infos = await apiGet("/api/accounts-info");

          let existing = null;
          if(curEmail && infos && infos.length > 0){
            existing = infos.find(a => a && a.email && a.email.toString().trim() === curEmail);
          }

          if(existing && existing.name){
            backup.name = existing.name;
          }else{
            const input = window.prompt("请输入备份别名（用于保存当前账号快照）:", "");
            if(!input || !input.trim()){
              toast("请先添加备份别名后再切换");
              return;
            }
            backup.name = input.trim();
          }
        }
        setStatus("切换中...");
        const data = await apiPost("/api/switch", {
          name,
          autoQuit,
          restartAfter,
          backup
        });

        // 备份如果跳过，则提示用户原因
        const tail = (data && data.restarted) ? "已尝试重新打开 Cursor。" : "如未自动打开，请手动启动 Cursor。";
        if(data && data.backup && data.backup.backup_skipped === "true" && data.backup.existing_name){
          toast(`切换完成（${tail}）（当前账号已存在于别名: ${data.backup.existing_name}，已跳过重复保存）`);
        }else{
          toast("切换完成：" + tail);
        }
        await refreshAll();
      }

      async function deleteAccountByName(name){
        const safeName = (name || "").toString().trim();
        if(!safeName){ toast("账号别名无效"); return; }
        const ok = confirm("确定删除账号别名: " + safeName + " 吗？删除后无法恢复该本地快照。");
        if(!ok) return;
        setStatus("删除中...");
        await apiPost("/api/delete", { name: safeName });
        toast("已删除账号: " + safeName);
        await refreshAll();
      }

      async function logoutAndQuit(){
        const ok = confirm("确定要退出当前账号（清空本地登录态）并关闭 Cursor 吗？");
        if(!ok) return;
        const autoQuit = true;
        setStatus("退出账号中...");
        await apiPost("/api/logout-quit", { autoQuit });
        toast("已退出账号，并请求关闭 Cursor。");
        setStatus("就绪");
        // 退出后本地 cursorAuth/* 已清空：刷新页面显示最新“当前账号”
        await refreshAll();
      }

      window.addEventListener("resize", () => syncTopCards());
      window.addEventListener("load", () => syncTopCards());
      window.onload = refreshAll;
    </script>
  </body>
</html>
"""


def json_response(handler: BaseHTTPRequestHandler, payload: Dict[str, Any], status: int = 200) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


class Handler(BaseHTTPRequestHandler):
    server_version = "CursorAccountSwitcherWeb/1.0"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            data = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            # 避免浏览器缓存旧页面（你截图里看到的勾选框就是典型的缓存旧版本现象）
            self.send_header("Cache-Control", "no-store, max-age=0, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(data)
            return

        if parsed.path == "/api/current":
            try:
                auth_map = core.read_auth_from_db(self.server.db_path)  # type: ignore[attr-defined]
                json_response(
                    self,
                    {
                        "email": auth_map.get("cursorAuth/cachedEmail", "-"),
                        "signup": auth_map.get("cursorAuth/cachedSignUpType", "-"),
                        "membership": auth_map.get("cursorAuth/stripeMembershipType", "-"),
                        "status": auth_map.get("cursorAuth/stripeSubscriptionStatus", "-"),
                    },
                )
            except Exception as exc:
                json_response(self, {"error": str(exc)}, status=500)
            return

        if parsed.path == "/api/accounts":
            try:
                names = core.list_account_names(self.server.backup_dir)  # type: ignore[attr-defined]
                json_response(self, {"accounts": names})
            except Exception as exc:
                json_response(self, {"error": str(exc)}, status=500)
            return

        if parsed.path == "/api/accounts-info":
            try:
                names = core.list_account_names(self.server.backup_dir)  # type: ignore[attr-defined]
                infos = []
                for name in names:
                    payload = core.load_account_payload(self.server.backup_dir, name)  # type: ignore[attr-defined]
                    saved_at = payload.get("saved_at", "-")
                    auth = payload.get("auth", {}) if isinstance(payload.get("auth", {}), dict) else {}
                    email = auth.get("cursorAuth/cachedEmail", "-")
                    signup = auth.get("cursorAuth/cachedSignUpType", "-")
                    membership = auth.get("cursorAuth/stripeMembershipType", "-")
                    infos.append(
                        {
                            "name": name,
                            "email": email if email else "-",
                            "signup": signup if signup else "-",
                            "membership": membership if membership else "-",
                            "saved_at": saved_at if saved_at else "-",
                        }
                    )
                # 保证 JSON 结构简单：前端直接渲染列表
                json_response(self, infos)
            except Exception as exc:
                json_response(self, {"error": str(exc)}, status=500)
            return

        json_response(self, {"error": "not found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            body = {}

        try:
            if parsed.path == "/api/save":
                name = str(body.get("name", "")).strip()
                if not name:
                    return json_response(self, {"error": "name is required"}, status=400)
                with self.server.op_lock:  # type: ignore[attr-defined]
                    if core.is_cursor_running() and bool(body.get("autoQuit", True)):
                        core.quit_cursor()
                    core.save_account(self.server.backup_dir, self.server.db_path, name)  # type: ignore[attr-defined]
                return json_response(self, {"ok": True, "name": name})

            if parsed.path == "/api/switch":
                name = str(body.get("name", "")).strip()
                if not name:
                    return json_response(self, {"error": "name is required"}, status=400)
                auto_quit = bool(body.get("autoQuit", True))
                restart_after = bool(body.get("restartAfter", True))
                backup = body.get("backup", {}) if isinstance(body.get("backup", {}), dict) else {}
                backup_enabled = bool(backup.get("enabled", False))
                backup_name = str(backup.get("name", "")).strip() if backup_enabled else ""
                if backup_enabled and not backup_name:
                    return json_response(self, {"error": "backup name is required"}, status=400)

                restarted = False
                with self.server.op_lock:  # type: ignore[attr-defined]
                    if core.is_cursor_running() and auto_quit:
                        core.quit_cursor()
                    backup_result = core.switch_account(  # type: ignore[attr-defined]
                        self.server.backup_dir,
                        self.server.db_path,
                        name,
                        backup_name or None,
                    )
                    # 切换写入后再启动 Cursor（仅当已退出且用户勾选“切换后重启”）
                    if auto_quit and restart_after and not core.is_cursor_running():
                        core.launch_cursor()
                        restarted = True
                return json_response(
                    self,
                    {"ok": True, "name": name, "backup": backup_result, "restarted": restarted},
                )

            if parsed.path == "/api/delete":
                name = str(body.get("name", "")).strip()
                if not name:
                    return json_response(self, {"error": "name is required"}, status=400)
                # 删除仅移除本地快照文件，不影响 Cursor 内登录态
                with self.server.op_lock:  # type: ignore[attr-defined]
                    core.delete_account(self.server.backup_dir, name)  # type: ignore[attr-defined]
                return json_response(self, {"ok": True, "name": name})

            if parsed.path == "/api/logout-quit":
                auto_quit = bool(body.get("autoQuit", True))
                # 先关闭 Cursor，避免写入数据库时发生竞争
                with self.server.op_lock:  # type: ignore[attr-defined]
                    if core.is_cursor_running() and auto_quit:
                        core.quit_cursor()
                    core.logout_current_account(self.server.db_path)  # type: ignore[attr-defined]
                    # 再请求一次关闭，确保“退出账号并关闭 Cursor”满足用户预期
                    if auto_quit:
                        core.quit_cursor()
                return json_response(self, {"ok": True})

            return json_response(self, {"error": "not found"}, status=404)
        except Exception as exc:
            return json_response(self, {"error": str(exc)}, status=500)

    def log_message(self, format: str, *args: Any) -> None:
        # 降噪：不在终端刷太多日志
        return


class WebServer(ThreadingHTTPServer):
    def __init__(self, server_address, RequestHandlerClass, db_path: Path, backup_dir: Path):
        super().__init__(server_address, RequestHandlerClass)
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.op_lock = threading.Lock()


def parse_args(argv: Optional[list[str]] = None) -> Any:
    import argparse

    p = argparse.ArgumentParser(description="Cursor 账号切换器 Web 界面")
    p.add_argument("--host", default=DEFAULT_HOST, help=f"监听地址（默认: {DEFAULT_HOST}）")
    p.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"端口（默认: {DEFAULT_PORT}）")
    p.add_argument(
        "--open-browser",
        action="store_true",
        help="启动后自动用默认浏览器打开页面",
    )
    p.add_argument(
        "--db-path",
        default=str(core.DEFAULT_DB_PATH),
        help="Cursor state.vscdb 路径",
    )
    p.add_argument(
        "--backup-dir",
        default=str(core.DEFAULT_BACKUP_DIR),
        help="快照保存目录",
    )
    return p.parse_args(argv)


def main() -> int:
    args = parse_args()
    db_path = Path(os.path.expanduser(args.db_path)).resolve()
    backup_dir = Path(os.path.expanduser(args.backup_dir)).resolve()

    server = WebServer(
        (args.host, args.port),
        Handler,
        db_path=db_path,
        backup_dir=backup_dir,
    )
    url = f"http://{args.host}:{args.port}/"
    print(f"服务已启动: {url}")
    if args.open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已退出服务。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

