#!/bin/bash
set -euxo pipefail
cd "$(dirname "$0")/../chronosGui2/forms"
PYQTDESIGNERPATH="${PYQTDESIGNERPATH:-}:../widgets" PYTHONPATH="${PYTHONPATH:-}:../:../../" designer