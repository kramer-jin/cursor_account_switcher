# -*- mode: python ; coding: utf-8 -*-
"""
后端（HTTP服务）打包规格：用于 Electron 内嵌 WebView。

在项目根目录执行示例：
  pyinstaller packaging/electron/backend.spec

产物：
  dist/CursorAccountSwitcherBackend/CursorAccountSwitcherBackend
"""
from pathlib import Path

block_cipher = None

SPECDIR = Path(SPECPATH).resolve()
ROOT = SPECDIR.parent.parent

a = Analysis(
    [str(SPECDIR / "backend_server.py")],
    pathex=[str(ROOT), str(SPECDIR)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CursorAccountSwitcherBackend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CursorAccountSwitcherBackend",
)

