#!/usr/bin/env python3
"""
deploy_seed.py - Deploya tu nodo seed público en 1 comando
Soporta: ngrok (prueba), VPS, Railway, Render
"""
import os
import sys
import subprocess
import json

print("🌍 BELCOIN - DEPLOY A INTERNET")
print("="*50)

print("\n1️⃣  ¿Dónde quieres desplegar?")
print("  1 - ngrok (prueba rápida, 2 min, URL temporal)")
print("  2 - VPS propio (IP pública permanente)")
print("  3 - Docker local (para probar red pública local)")
print("  4 - Generar instrucciones para Railway/Render/Fly.io")

op = input("\nElige opción (1-4): ").strip()

if op == "1":
    print("\n📡 Opción ngrok seleccionada")
    print("Instalando ngrok...")
    # Verificar si ngrok está instalado
    try:
        subprocess.run(["ngrok", "version"], capture_output=True, check=True)
    except:
        print("❌ ngrok no encontrado. Instalalo:")
        print("   npm install -g ngrok  o  brew install ngrok")
        print("   Luego: ngrok authtoken TU_TOKEN")
        sys.exit(1)
    
    print("\n🚀 Levantando nodo local en 0.0.0.0:5000...")
    nodo = subprocess.Popen([sys.executable, "main_multinodo.py", "--host", "0.0.0.0", "--port", "5000", "--mining", "--difficulty", "4"])
    
    print("🌐 Exponiendo con ngrok...")
    print("   Comparte esta URL con tus amigos para que se conecten:")
    print("\n   En otra terminal corre: ngrok http 5000")
    print("\n   Ellos se conectan con:")
    print("   python main_multinodo.py --mining --peer https://TU_URL_NGROK.ngrok.io")
    
    try:
        nodo.wait()
    except KeyboardInterrupt:
        nodo.terminate()

elif op == "2":
    print("\n🖥️  VPS - Instrucciones:")
    print("""
1. En tu VPS (Ubuntu):
   git clone https://github.com/TU_USER/belcoin.git
   cd belcoin
   cp blockchain_fixed.py blockchain.py
   pip3 install -r requirements.txt

2. Abre puerto:
   sudo ufw allow 5000/tcp
   sudo ufw allow 22/tcp
   sudo ufw enable

3. Levanta con tmux:
   tmux new -s belcoin
   python3 main_multinodo.py --host 0.0.0.0 --port 5000 --mining --difficulty 5
   # Ctrl+B luego D para salir

4. Tu IP pública es tu SEED:
   curl ifconfig.me
   # Ejemplo: 45.33.12.10

5. Comparte con amigos:
   python main_multinodo.py --mining --peer http://45.33.12.10:5000

6. Para ver logs:
   tmux attach -t belcoin
""")

elif op == "3":
    print("\n🐳 Docker local - Red de 3 nodos compitiendo")
    os.system("docker-compose up --build")

elif op == "4":
    print("""
☁️  RAILWAY / RENDER / FLY.IO - Deploy gratis

1. Sube tu repo a GitHub (con este README_PUBLIC.md como README.md)

2. Railway.app:
   - New Project -> Deploy from GitHub
   - Selecciona tu repo belcoin
   - Settings -> Port: 5000
   - Deploy -> Te da URL tipo https://belcoin.up.railway.app

3. En tu repo, edita seeds.json:
   {
     "seeds": ["https://belcoin.up.railway.app"]
   }

4. Los demás se conectan:
   python main_multinodo.py --mining --peer https://belcoin.up.railway.app

¡Listo! Red pública sin pagar VPS.
""")

print("\n✅ Hecho")
