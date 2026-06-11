#!/bin/bash
# Sobe o projeto Swift NPS (backend + frontend no mesmo servidor)

cd "$(dirname "$0")"

PYTHON=python3.11

echo "📦 Verificando dependências..."
$PYTHON -m pip install -r backend/requirements.txt -q --break-system-packages 2>/dev/null || true

# Mata processo anterior se estiver rodando
lsof -ti:5050 | xargs kill -9 2>/dev/null || true
sleep 1

echo ""
echo "🚀 Subindo Swift NPS Analytics em http://localhost:5050"
echo "Para encerrar: Ctrl+C"
echo "---"

$PYTHON backend/api.py &
PID=$!
echo "⏳ Aguardando carregamento dos dados..."
sleep 6

echo "✅ Pronto! Acesse: http://localhost:5050"

trap "kill $PID 2>/dev/null; echo 'Encerrado.'" EXIT
wait

