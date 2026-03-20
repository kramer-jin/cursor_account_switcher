# -*- mode: python ; coding: utf-8 -*-
"""
在项目根目录（IdeaProjects/solution）执行：
  pip install pyinstaller
  pyinstaller packaging/macos/cursor_account_switcher.spec

产物：dist/Cursor账号切换器.app
"""
from pathlib import Path

block_cipher = None

SPECDIR = Path(SPECPATH).resolve()
ROOT = SPECDIR.parent.parent

a = Analysis(
    [str(SPECDIR / "launcher.py")],
    pathex=[str(ROOT), str(SPECDIR)],
    binaries=[],
    datas=[
        (str(ROOT / "cursor_account_switcher.py"), "."),
        (str(ROOT / "cursor_account_switcher_web.py"), "."),
    ],
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
    name="CursorAccountSwitcher",
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
    name="CursorAccountSwitcher",
)

app = BUNDLE(
    coll,
    name="Cursor账号切换器.app",
    icon=None,
    bundle_identifier="dev.kramer.cursor-account-switcher",
    info_plist={
        "CFBundleName": "Cursor账号切换器",
        "CFBundleDisplayName": "Cursor账号切换器",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "10.13",
        "NSHumanReadableCopyright": "Copyright © 2026 Personal use",
    },
)

