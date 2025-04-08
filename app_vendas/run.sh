#!/bin/bash

# Script para iniciar a aplicação Dashboard de Vendas

echo "Iniciando Dashboard de Vendas..."
echo "Verificando dependências..."

# Verificar se o Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "Python 3 não encontrado. Por favor, instale o Python 3."
    exit 1
fi

# Verificar se o pip está instalado
if ! command -v pip3 &> /dev/null; then
    echo "pip3 não encontrado. Por favor, instale o pip."
    exit 1
fi

# Criar ambiente virtual se não existir
if [ ! -d "venv" ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv venv
fi

# Ativar ambiente virtual
echo "Ativando ambiente virtual..."
source venv/bin/activate

# Instalar dependências
echo "Instalando dependências..."
pip install -r requirements.txt

# Iniciar a aplicação
echo "Iniciando servidor..."
python app.py

# Desativar ambiente virtual ao sair
deactivate 