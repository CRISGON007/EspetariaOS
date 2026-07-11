#!/bin/bash

set -e

echo "======================================="
echo " EspetariaOS - Instalação"
echo "======================================="

# Verifica Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python3 não encontrado."
    exit 1
fi

# Verifica venv
if ! python3 -c "import venv" >/dev/null 2>&1; then
    echo "Instalando python3-venv..."
    sudo apt update
    sudo apt install -y python3-venv
fi

# Cria ambiente virtual
if [ ! -d ".venv" ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv .venv
fi

# Ativa ambiente
source .venv/bin/activate

echo "Atualizando pip..."
python -m pip install --upgrade pip

echo "Instalando dependências..."
pip install -r requirements.txt

# Cria diretórios necessários
mkdir -p data
mkdir -p logs
mkdir -p backups

echo ""
echo "======================================="
echo "Instalação concluída com sucesso!"
echo "======================================="
echo ""
echo "Para iniciar o sistema execute:"
echo ""
echo "./start.sh"
echo ""
