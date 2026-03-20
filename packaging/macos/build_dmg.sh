#!/usr/bin/env bash
# 在「项目根目录」solution/ 下执行：
#   bash packaging/macos/build_dmg.sh
#
# 依赖：本机 python3；PyInstaller 会在虚拟环境 .venv-build-pyi 中安装（避免 Homebrew PEP 668 限制）。

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

APP_NAME="Cursor账号切换器.app"
DIST_APP="dist/${APP_NAME}"
DMG_NAME="dist/Cursor账号切换器.dmg"
VENV="${ROOT}/.venv-build-pyi"

command -v python3 >/dev/null || { echo "需要 python3"; exit 1; }

if [[ ! -x "${VENV}/bin/pyinstaller" ]]; then
  echo ">>> 创建虚拟环境并安装 PyInstaller: ${VENV}"
  python3 -m venv "${VENV}"
  "${VENV}/bin/pip" install -q --upgrade pip
  "${VENV}/bin/pip" install -q pyinstaller
fi

echo ">>> 打包 .app ..."
rm -rf build dist
"${VENV}/bin/pyinstaller" --noconfirm packaging/macos/cursor_account_switcher.spec

if [[ ! -d "${DIST_APP}" ]]; then
  echo "未找到 ${DIST_APP}，请查看 pyinstaller 报错"
  exit 1
fi

echo ">>> 生成 DMG ..."
if command -v create-dmg >/dev/null 2>&1; then
  rm -f "${DMG_NAME}"
  create-dmg \
    --volname "Cursor账号切换器" \
    --window-pos 200 120 \
    --window-size 660 420 \
    --icon-size 88 \
    --hide-extension "${APP_NAME}" \
    --app-drop-link 480 218 \
    "${DMG_NAME}" \
    "${DIST_APP}"
  echo "完成: ${DMG_NAME}"
else
  echo "未安装 create-dmg，仅生成 .app：${DIST_APP}"
  echo "可选：brew install create-dmg 后重新运行本脚本以生成 DMG"
fi

