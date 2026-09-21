#!/bin/bash
echo "Starting Belcoin 2009 Retro Network..."
python main.py --port 5000 --mining &
python main.py --port 5001 --mining --peer http://localhost:5000 &
echo "Nodes running: 5000 (seed) and 5001"
echo "Open http://localhost:5000 for retro wallet"
