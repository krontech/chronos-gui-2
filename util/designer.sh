#!/bin/bash
set -euxo pipefail
cd "$(dirname "$0")/../src/screens"
PYQTDESIGNERPATH="${PYQTDESIGNERPATH:-}:../widgets" PYTHONPATH="${PYTHONPATH:-}:../" designer