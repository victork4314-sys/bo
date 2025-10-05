#!/usr/bin/env bash
set -euo pipefail

PYODIDE_VERSION=${PYODIDE_VERSION:-0.24.1}
DIST_DIR="dist"
PYODIDE_ZIP="pyodide-${PYODIDE_VERSION}.zip"
PYODIDE_URL="https://github.com/pyodide/pyodide/releases/download/${PYODIDE_VERSION}/${PYODIDE_ZIP}"

rm -rf "${DIST_DIR}"
mkdir -p "${DIST_DIR}"

python -m compileall core >/dev/null

python <<'PY'
import json
import sys
from pathlib import Path

sys.path.append(str(Path('core').resolve()))
from biospeak_core.filemap import generate_file_map

output = Path('dist/file-map.json')
output.write_text(json.dumps(generate_file_map(Path('.')), indent=2), encoding='utf-8')
PY

cp -R web/. "${DIST_DIR}/"
cp -R core/. "${DIST_DIR}/core/"

mkdir -p "${DIST_DIR}/pyodide"
if [ ! -f "${PYODIDE_ZIP}" ]; then
  curl -L -o "${PYODIDE_ZIP}" "${PYODIDE_URL}"
fi
unzip -q "${PYODIDE_ZIP}" -d "${DIST_DIR}/pyodide_tmp"
cp -R "${DIST_DIR}/pyodide_tmp/pyodide-${PYODIDE_VERSION}/." "${DIST_DIR}/pyodide/"
rm -rf "${DIST_DIR}/pyodide_tmp"

printf '\nBuild complete — web version operational\n'
