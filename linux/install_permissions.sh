#!/bin/bash
set -e

APP_NAME="bledot-metrics-extractor"
SUDOERS_FILE_NAME="99-$APP_NAME"

uninstall() {
    echo "=> Removendo a regra de sudoers /etc/sudoers.d/$SUDOERS_FILE_NAME..."
    rm -f "/etc/sudoers.d/$SUDOERS_FILE_NAME"
    echo "Regra de sudoers removida."
}

install() {
    if [ -z "$SUDO_USER" ]; then
        echo "ERRO: Este script deve ser executado com 'sudo' por um usuário normal para detectar o nome de usuário."
        exit 1
    fi

    echo "=> Configurando permissões de sudo para o usuário '$SUDO_USER'..."
    COMMANDS=(
        "/usr/sbin/dmidecode"
        "/usr/sbin/smartctl"
        "/usr/bin/journalctl"
        "/usr/bin/apt"
        "/usr/sbin/ufw"
        "/usr/bin/which"
    )
    COMMANDS_NOPASSWD=$(IFS=, ; echo "${COMMANDS[*]}")
    SUDOERS_RULE="$SUDO_USER ALL=(ALL) NOPASSWD: $COMMANDS_NOPASSWD"
    
    echo "$SUDOERS_RULE" > /tmp/$SUDOERS_FILE_NAME
    visudo -cf /tmp/$SUDOERS_FILE_NAME
    
    mv /tmp/$SUDOERS_FILE_NAME /etc/sudoers.d/
    chmod 0440 "/etc/sudoers.d/$SUDOERS_FILE_NAME"
    
    echo "Permissões configuradas com sucesso."
    echo ""
    echo "----------------------------------------------------------------"
    echo "PRÓXIMO PASSO: Execute o segundo script SEM sudo:"
    echo "./configure_user_service.sh"
    echo "----------------------------------------------------------------"
}

# --- Lógica Principal ---
if [ "$(id -u)" -ne 0 ]; then
  echo "Este script precisa ser executado com 'sudo'. Ex: sudo ./install_permissions.sh"
  exit 1
fi

if [ "$1" == "--uninstall" ]; then
    uninstall
else
    install
fi
