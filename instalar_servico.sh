#!/usr/bin/env bash
set -Eeuo pipefail
[[ "$EUID" -eq 0 ]] || { echo "Use: sudo ./instalar_servico.sh"; exit 1; }
SRC="$(cd "$(dirname "$0")" && pwd)"
TARGET=/opt/espetariaos
DATA=/var/lib/espetariaos
LOG=/var/log/espetariaos
id espetariaos >/dev/null 2>&1 || useradd --system --home "$TARGET" --shell /usr/sbin/nologin espetariaos
mkdir -p "$TARGET" "$DATA/backups" "$LOG"
rsync -a --delete --exclude='.git/' --exclude='.venv/' --exclude='data/*.db*' --exclude='backups/*' --exclude='logs/*' "$SRC/" "$TARGET/"
python3 -m venv "$TARGET/.venv"
"$TARGET/.venv/bin/python" -m pip install --upgrade pip
"$TARGET/.venv/bin/python" -m pip install -r "$TARGET/requirements.txt"
install -m 0644 "$TARGET/systemd/espetariaos.service" /etc/systemd/system/espetariaos.service
chown -R espetariaos:espetariaos "$TARGET" "$DATA" "$LOG"
systemctl daemon-reload
systemctl enable --now espetariaos
systemctl --no-pager --full status espetariaos
