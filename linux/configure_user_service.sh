#!/bin/bash
set -e

APP_NAME="bledot-metrics-extractor"
TIMER_PERIOD="10min"
RUN_SCRIPT_NAME="run_extraction.py"
VENV_DIR="bledot-env"
WORK_DIR=$(cd "$(dirname "$0")/.." && pwd)

uninstall() {
    echo "=> Parando e desabilitando o timer do usuário..."
    systemctl --user disable --now "$APP_NAME.timer" &>/dev/null || true
    
    echo "=> Removendo arquivos de serviço do usuário..."
    rm -f "$HOME/.config/systemd/user/$APP_NAME.service"
    rm -f "$HOME/.config/systemd/user/$APP_NAME.timer"

    echo "=> Recarregando o systemd do usuário..."
    systemctl --user daemon-reload
    echo "Serviço de usuário desinstalado."
}

install() {
    echo "=> Instalando o serviço systemd para o usuário atual..."
    USER_SERVICE_DIR="$HOME/.config/systemd/user"
    mkdir -p "$USER_SERVICE_DIR"

    PYTHON_EXEC="$WORK_DIR/$VENV_DIR/bin/python"
    RUN_SCRIPT_PATH="$WORK_DIR/linux/$RUN_SCRIPT_NAME"

    # Cria os arquivos .service e .timer
    cat > "$USER_SERVICE_DIR/$APP_NAME.service" << EOF
[Unit]
Description=Bledot Metrics Extractor Service (User)
Wants=graphical-session.target
After=graphical-session.target
[Service]
Type=oneshot
WorkingDirectory=$WORK_DIR
ExecStart=$PYTHON_EXEC $RUN_SCRIPT_PATH
[Install]
WantedBy=default.target
EOF

    cat > "$USER_SERVICE_DIR/$APP_NAME.timer" << EOF
[Unit]
Description=Roda o Bledot Metrics Extractor a cada $TIMER_PERIOD (User)
[Timer]
OnBootSec=2min
OnUnitActiveSec=$TIMER_PERIOD
Persistent=true
[Install]
WantedBy=timers.target
EOF

    # Ativa o serviço e o timer
    systemctl --user daemon-reload
    systemctl --user enable --now "$APP_NAME.timer"
    echo "Serviço de usuário instalado e ativado com sucesso."
}

# --- Lógica Principal ---
if [ "$(id -u)" -eq 0 ]; then
  echo "Este script NÃO deve ser executado com 'sudo'."
  exit 1
fi

if [ "$1" == "--uninstall" ]; then
    uninstall
else
    install
fi
