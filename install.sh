#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
set -eu
cd -- "$(dirname -- "$0")"
exec /usr/bin/python3 easy.py "$@"
