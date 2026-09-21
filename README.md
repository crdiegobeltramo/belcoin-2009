# ₿ BELCOIN - Bitcoin Core 2009 Retro Edition

![Retro](https://img.shields.io/badge/Wallet-Bitcoin%20Core%200.1%20Alpha%20(2009)-blue?style=for-the-badge)
![Generate Coins](https://img.shields.io/badge/Button-GENERATE%20COINS-red?style=for-the-badge)

> **Belcoin con interfaz exacta de Bitcoin Core v0.1 de Satoshi Nakamoto 2009. Incluye el legendario botón Generate Coins.**

## 🖥️ Nuevo Dashboard Retro 2009

Este repo viene con el dashboard retro integrado en `http://localhost:5000`:

- Ventana Windows XP estilo Bitcoin 0.1 Alpha
- Menú File | Settings -> **Generate Coins** | Help
- Botón Send Coins con IP address
- Tabla All Transactions con Status | Date | Description | Debit | Credit
- Status bar: 3 connections | 213 blocks | 2 transactions
- Modal Generate Coins con Limit processors, hash rate y mining log

## 🚀 Levantar en 30 segundos

```bash
git clone https://github.com/TU_USER/belcoin.git
cd belcoin
pip install -r requirements.txt
python api.py
# Abrir http://localhost:5000 - Ya ves la wallet 2009
```

Con minería:

```bash
python main.py --port 5000 --mining
# o red local:
./start_network.sh
```

# ₿ BELCOIN - Mi propio Bitcoin en Python

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![PoW](https://img.shields.io/badge/Proof%20of%20Work-SHA256-orange?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

> **Blockchain tipo Bitcoin en Python puro con PoW real, Longest Chain Rule, red P2P y carrera de minería. Cualquiera puede clonar y competir minando bloques.**

**Seed público 24/7:** `https://belcoin-production.up.railway.app` ✅ Live

**Demo:** [Ver carrera en vivo](https://belcoin-production.up.railway.app/blocks) | **Docker:** `crdiegobeltramo/belcoin:latest`

---

## 🚀 Únete en 30 segundos

### Opción 1: Python (recomendado para devs)
```bash
git clone https://github.com/TU_USER/belcoin.git
cd belcoin
pip install -r requirements.txt
python main.py --mining --peer https://belcoin-production.up.railway.app
# Ya estás minando contra la red pública. 50 BEL por bloque.
```

### Opción 2: Docker - 1 comando (para cualquiera)
```bash
docker run -d -p 5000:5000 crdiegobeltramo/belcoin:latest python main.py --host 0.0.0.0 --port 5000 --mining --peer https://belcoin-production.up.railway.app
```

### Opción 3: Red local - Compite contra vos mismo
```bash
./start_network.sh  # Levanta 2 nodos en 5000 y 5001 compitiendo
python race_viewer.py  # Ve la carrera en tiempo real
./stop_network.sh
```

---

## ⛏️ ¿Qué es Belcoin?

Belcoin es una blockchain educativa tipo Bitcoin implementada desde cero en Python:

- **Proof-of-Work real:** SHA256 con dificultad ajustable (default 4 ceros `0000`)
- **Longest Chain Rule:** Reorg automático como Bitcoin Core
- **Génesis determinístico:** Todos los nodos comparten el mismo bloque 0 (timestamp fijo)
- **UTXO + Wallets:** Transacciones firmadas, validación de balance
- **P2P real:** Nodos se descubren, sincronizan `/blocks` y resuelven forks
- **50 BEL por bloque:** Recompensa de coinbase, halving configurable

### ¿Por qué competían mis nodos antes y ahora sí?

3 bugs fixeados en esta versión mainnet:

1.  **Génesis aleatorio** `time.time()` → Fix: `GENESIS_TIMESTAMP = 1700000000.0` fijo
2.  **Sync sin reorg** solo aceptaba siguiente bloque → Fix: `sync_chain()` valida cadena completa y reemplaza si es más larga
3.  **localhost** no sirve en internet → Fix: `0.0.0.0` + validación PoW + rechazo génesis diferente

---

## 📊 Estado de la red

**Seed principal:**
```
https://belcoin-production.up.railway.app
  /blocks  -> cadena completa
  /health  -> healthcheck
  /peers   -> peers conectados
```

**Ver altura actual:**
```bash
curl https://belcoin-production.up.railway.app/blocks | python -m json.tool | grep -c "index"
# o
curl -s https://belcoin-production.up.railway.app/blocks | jq length
```

**Record actual:** 12 bloques seguidos por un mismo minero

---

## 🐳 Docker

**Build local:**
```bash
docker build -t belcoin .
docker run -d -p 5000:5000 belcoin
```

**Docker Hub (público):**
```bash
docker pull crdiegobeltramo/belcoin:latest
docker run -d -p 5000:5000 --name belcoin-seed crdiegobeltramo/belcoin:latest
# Logueate
docker login
# Pushear (si hiciste cambios)
./docker-push.sh crdiegobeltramo
```

**docker-compose - 3 nodos compitiendo:**
```bash
docker-compose up --build
# Levanta nodo1:5000, nodo2:5001, nodo3:5002 todos minando y compitiendo
docker-compose down
```

---

## 🌐 Deploy gratis sin pagar VPS

**Railway.app (recomendado):**
1. Sube repo a GitHub
2. railway.app → New Project → Deploy from GitHub repo
3. Detecta `Dockerfile` + `railway.json` automático
4. Te da URL: `https://belcoin-xxxx.up.railway.app` → agregala a `seeds.json`

**Render.com:**
- New → Web Service → Runtime: Docker → Health Check: `/health`

**Fly.io:**
```bash
fly launch --no-deploy
fly deploy
# URL: https://belcoin-seed.fly.dev
```

Archivos ya incluidos: `railway.json`, `render.yaml`, `fly.toml`, `Procfile`, `start.sh`

---

## 📁 Estructura

```
belcoin/
├── main.py              # Entry point --host --port --mining --peer
├── blockchain.py         # Blockchain, Block, Transaction, PoW, UTXO, génesis fijo
├── block.py             # Clase Block (tu original)
├── transaction.py       # Clase Transaction (tu original)
├── wallet.py            # Wallet + firma
├── miner.py             # Minero PoW
├── network.py           # P2P + sync_chain con reorg + longest chain
├── api.py               # Flask API 0.0.0.0 + /blocks /health /peers
├── seeds.json           # Seeds públicos
├── race_viewer.py       # Visor carrera en vivo
├── Dockerfile           # Docker listo para internet
├── docker-compose.yml   # 3 nodos compitiendo local
├── requirements.txt     # flask, requests
└── README.md            # Este archivo
```

**API Endpoints:**
- `GET /blocks` → cadena completa
- `GET /health` → {"status":"ok","height":127,"peers":3}
- `GET /peers` → lista peers
- `POST /add_node` → {"address":"http://ip:port"}

---

## 🏁 Carrera de minería

```bash
python race_viewer.py
```
Muestra en tiempo real:
- Altura de cada nodo
- Hash del último bloque
- Tiempo de minado
- Forks y reorgs
- Ganador por bloque

¡Haz tu propia carrera con amigos!

---

## 🤝 Cómo competir por bloques

1. Clona y corre con `--mining --peer SEED_PUBLICO`
2. Tu nodo empieza a hashear buscando nonce con `0000...`
3. Si lo encuentras primero, lo propagas a todos los peers con `POST /add_block`
4. Los demás validan PoW y lo adoptan si tu cadena es más larga
5. Ganas 50 BEL (balance en tu wallet)

**Tip:** Baja dificultad para pruebas rápidas:
```bash
python main.py --mining --difficulty 2 --peer https://...
```

---

## 📺 Video tutorial

**YouTube:** [Construí mi propio Bitcoin en Python y ahora cualquiera puede robarme bloques](https://youtube.com/...) - Próximamente

Guión completo + miniatura en `/docs`

---

## 📜 Licencia

MIT - Haz lo que quieras, mina lo que puedas.

---

## 👨‍💻 Autor

**Diego Beltramo** - [@crdiegobeltramo](https://instagram.com/crdiegobeltramo)

Si llegás a altura 200 antes que yo en la red pública, te menciono en el próximo video. ¡Nos vemos en la cadena!

**¿Cuántos bloques me pudiste robar?** Comenta tu altura en Issues.

