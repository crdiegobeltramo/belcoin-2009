#!/usr/bin/env python3
"""
🏁 Belcoin Race Live Viewer - Linux
Muestra en tiempo real qué nodo va ganando la carrera de minería
"""
import requests
import time
import os
from datetime import datetime

NODO1 = "http://localhost:5000"
NODO2 = "http://localhost:5001"

# Colores ANSI
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"
GRAY = "\033[90m"

def get_info(url):
    try:
        h = requests.get(f"{url}/health", timeout=1).json()
        blocks = requests.get(f"{url}/blocks", timeout=2).json()
        wallets = requests.get(f"{url}/wallets", timeout=1).json()
        mining = requests.get(f"{url}/mining/status", timeout=1).json()
        return {
            "online": True,
            "height": h.get("blockchain_height", len(blocks)),
            "blocks": blocks,
            "wallets": wallets,
            "mining": mining,
            "is_mining": mining.get("is_mining", False) if isinstance(mining, dict) else False
        }
    except Exception as e:
        return {"online": False, "error": str(e), "height": 0, "blocks": [], "wallets": []}

def get_miner_address(block):
    try:
        # coinbase es la primera tx
        txs = block.get("transactions", [])
        if txs:
            # La coinbase tiene outputs con address del minero
            outputs = txs[0].get("outputs", [])
            if outputs:
                return outputs[0].get("address", "unknown")
        return "unknown"
    except:
        return "unknown"

def clear():
    os.system("clear")

# Mapeo de direcciones a nodos
known_wallets = {}

race_history = []

print(f"{BOLD}{CYAN}🏁 Iniciando visor de carrera Belcoin...{RESET}")
print(f"Conectando a {NODO1} y {NODO2}")
print()

last_heights = {NODO1: 0, NODO2: 0}

try:
    while True:
        clear()
        now = datetime.now().strftime("%H:%M:%S")
        
        info1 = get_info(NODO1)
        info2 = get_info(NODO2)
        
        # Actualizar mapa de wallets
        for w in info1.get("wallets", []):
            known_wallets[w.get("address")] = "NODO 1"
        for w in info2.get("wallets", []):
            known_wallets[w.get("address")] = "NODO 2"
        
        print(f"{BOLD}╔══════════════════════════════════════════════════════════════╗{RESET}")
        print(f"{BOLD}║  🚀 BELCOIN - CARRERA DE MINERÍA EN VIVO  [{now}]        ║{RESET}")
        print(f"{BOLD}╚══════════════════════════════════════════════════════════════╝{RESET}")
        print()
        
        # Estado nodos
        status1 = f"{GREEN}● ONLINE{RESET}" if info1["online"] else f"{RED}● OFFLINE{RESET}"
        status2 = f"{GREEN}● ONLINE{RESET}" if info2["online"] else f"{RED}● OFFLINE{RESET}"
        
        mining1 = f"{YELLOW}⛏ MINANDO{RESET}" if info1.get("is_mining") else f"{GRAY}⏸ parado{RESET}"
        mining2 = f"{YELLOW}⛏ MINANDO{RESET}" if info2.get("is_mining") else f"{GRAY}⏸ parado{RESET}"
        
        print(f"{BOLD}NODO 1 (5000):{RESET} {status1} | Altura: {BOLD}{info1['height']}{RESET} | {mining1}")
        if info1["wallets"]:
            addr1 = info1["wallets"][0].get("address", "")[:20] + "..."
            bal1 = info1["wallets"][0].get("balance", 0)
            print(f"  Wallet: {GRAY}{addr1}{RESET} | Balance: {GREEN}{bal1} BEL{RESET}")
        
        print(f"{BOLD}NODO 2 (5001):{RESET} {status2} | Altura: {BOLD}{info2['height']}{RESET} | {mining2}")
        if info2["wallets"]:
            addr2 = info2["wallets"][0].get("address", "")[:20] + "..."
            bal2 = info2["wallets"][0].get("balance", 0)
            print(f"  Wallet: {GRAY}{addr2}{RESET} | Balance: {GREEN}{bal2} BEL{RESET}")
        
        print()
        print(f"{BOLD}─ Blockchain (últimos 10 bloques) ─{RESET}")
        
        # Usar bloques del nodo con más altura
        all_blocks = info1["blocks"] if len(info1["blocks"]) >= len(info2["blocks"]) else info2["blocks"]
        if not all_blocks and info2["blocks"]:
            all_blocks = info2["blocks"]
        
        if all_blocks:
            # Detectar nuevo bloque
            latest_height = len(all_blocks)
            if latest_height > max(last_heights.values()):
                newest = all_blocks[-1]
                miner_addr = get_miner_address(newest)
                owner = known_wallets.get(miner_addr, "DESCONOCIDO")
                if owner == "NODO 1":
                    race_history.append((latest_height, "NODO 1", miner_addr, now))
                elif owner == "NODO 2":
                    race_history.append((latest_height, "NODO 2", miner_addr, now))
                else:
                    # Si no conocemos wallet, inferir por altura previa
                    if info1["height"] > last_heights[NODO1]:
                        race_history.append((latest_height, "NODO 1", miner_addr, now))
                    elif info2["height"] > last_heights[NODO2]:
                        race_history.append((latest_height, "NODO 2", miner_addr, now))
            
            last_heights[NODO1] = info1["height"]
            last_heights[NODO2] = info2["height"]
            
            # Mostrar últimos 10
            for b in all_blocks[-10:][::-1]:
                idx = b.get("index", "?")
                h = b.get("hash", "")[:16]
                miner = get_miner_address(b)
                owner = known_wallets.get(miner, "?")
                
                if owner == "NODO 1":
                    color = CYAN
                    emoji = "🟦"
                elif owner == "NODO 2":
                    color = GREEN
                    emoji = "🟩"
                else:
                    color = GRAY
                    emoji = "⬜"
                
                ts = datetime.fromtimestamp(b.get("timestamp", 0)).strftime("%H:%M:%S") if b.get("timestamp") else "??:??:??"
                print(f"  {emoji} {color}Bloque #{idx:3}{RESET} | {GRAY}{h}...{RESET} | {color}{owner:8}{RESET} | {ts} | nonce: {b.get('nonce', 0)}")
        else:
            print(f"  {GRAY}Sin bloques aún... esperando génesis{RESET}")
        
        print()
        # Marcador
        count1 = sum(1 for r in race_history if r[1] == "NODO 1")
        count2 = sum(1 for r in race_history if r[1] == "NODO 2")
        
        print(f"{BOLD}─ Marcador ─{RESET}")
        bar_len = 30
        total = count1 + count2
        if total > 0:
            p1 = int((count1 / total) * bar_len) if total else 0
            p2 = bar_len - p1
            print(f"  NODO 1 {CYAN}{'█'*p1}{RESET}{GRAY}{'░'*p2}{RESET} NODO 2")
        print(f"  {CYAN}NODO 1: {count1} bloques{RESET} | {GREEN}NODO 2: {count2} bloques{RESET} | Total: {len(all_blocks)}")
        
        if count1 > count2:
            print(f"  {BOLD}{CYAN}🏆 Va ganando NODO 1 por {count1-count2}{RESET}")
        elif count2 > count1:
            print(f"  {BOLD}{GREEN}🏆 Va ganando NODO 2 por {count2-count1}{RESET}")
        else:
            if total > 0:
                print(f"  {YELLOW}🤝 Empatados!{RESET}")
        
        print()
        print(f"{GRAY}Presiona Ctrl+C para salir | Actualiza cada 2s | Log: tail -f nodo*.log{RESET}")
        
        time.sleep(2)

except KeyboardInterrupt:
    print(f"\n{YELLOW}🛑 Visor detenido{RESET}")
    print(f"Historial final: Nodo1={count1} Nodo2={count2}")
