#!/bin/bash
# Start script para Railway/Render/Fly
PORT=${PORT:-5000}
echo "🚀 Iniciando Belcoin Seed en 0.0.0.0:$PORT"
python main.py --host 0.0.0.0 --port $PORT --mining --difficulty 5
