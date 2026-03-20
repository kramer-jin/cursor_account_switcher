#!/usr/bin/env bash
# 在项目根目录执行：
#   bash packaging/electron-app/build.sh
#
# 产物：
#   packaging/electron-app/dist/*.dmg 以及相关 .app

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ELECTRON_DIR="${ROOT}/packaging/electron-app"

APP_NAME="Cursor账号切换器"
BACKEND_BINARY_NAME="CursorAccountSwitcherBackend"

VENV="${ROOT}/.venv-build-pyi-electron"
BACKEND_DIST_DIR="${ELECTRON_DIR}/dist-backend"
BACKEND_WORK_DIR="${ELECTRON_DIR}/build-backend"

command -v python3 >/dev/null || { echo "需要 python3"; exit 1; }
command -v npm >/dev/null || { echo "需要 npm（Node.js）"; exit 1; }

echo ">>> 准备 Electron 依赖..."
cd "$ELECTRON_DIR"
if [[ ! -d "node_modules" ]]; then
  npm install
fi

echo ">>> 准备 PyInstaller 环境: ${VENV}"
if [[ ! -x "${VENV}/bin/pyinstaller" ]]; then
  python3 -m venv "${VENV}"
  "${VENV}/bin/pip" install -q --upgrade pip
  "${VENV}/bin/pip" install -q pyinstaller
fi

echo ">>> 打包后端二进制..."
rm -rf "${BACKEND_DIST_DIR}" "${BACKEND_WORK_DIR}"
"${VENV}/bin/pyinstaller" \
  --noconfirm \
  --distpath "${BACKEND_DIST_DIR}" \
  --workpath "${BACKEND_WORK_DIR}" \
  "${ROOT}/packaging/electron/backend.spec"

BACKEND_DIR_SRC="${BACKEND_DIST_DIR}/${BACKEND_BINARY_NAME}"
BACKEND_BIN="${BACKEND_DIR_SRC}/${BACKEND_BINARY_NAME}"
if [[ ! -f "$BACKEND_BIN" ]]; then
  echo "未找到后端二进制：$BACKEND_BIN"
  exit 1
fi

echo ">>> 拷贝后端到 Electron resources..."
rm -rf "${ELECTRON_DIR}/resources/backend"
mkdir -p "${ELECTRON_DIR}/resources/backend"
cp -aL "${BACKEND_DIR_SRC}/." "${ELECTRON_DIR}/resources/backend/"

echo ">>> 构建 macOS DMG..."
rm -rf "${ELECTRON_DIR}/dist"
npm run package

echo "完成。DMG 路径见：${ELECTRON_DIR}/dist"

