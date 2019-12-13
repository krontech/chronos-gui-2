#!/bin/bash
set -euxo pipefail
cd "$(dirname "$0")/../chronosGui2/screens"
PYQTDESIGNERPATH="${PYQTDESIGNERPATH:-}:../widgets" PYTHONPATH="${PYTHONPATH:-}:../:../../" qtcreator