#!/usr/bin/env python3
"""
Nodo Belcoin mejorado para competencia multi-nodo
Soporta --peer para conectarse automáticamente
"""
import time
import threading
import argparse
import signal
import sys
import requests
from blockchain import Blockchain
from wallet import WalletManager
from miner import Miner
from network import NetworkManager
from api import BelcoinAPI

class BelcoinNode:
    def __init__(self, host: str = "localhost", port: int = 5000, 
                 enable_mining: bool = False, enable_network: bool = True,
                 peer: str = None):
        print(f"🚀 Iniciando nodo de Belcoin en {host}:{port}...")
        
        self.blockchain = Blockchain()
        self.wallet_manager = WalletManager()
        self.network_manager = None
        self.miner = None
        self.api = None
        
        self.host = host
        self.port = port
        self.enable_mining = enable_mining
        self.enable_network = enable_network
        self.peer = peer
        
        self.is_running = False
        self.shutdown_event = threading.Event()
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        print("✅ Nodo inicializado")
    
    def start(self):
        try:
            print("🔄 Iniciando servicios...")
            
            if not self.wallet_manager.wallets:
                default_wallet = self.wallet_manager.create_wallet("default")
                print(f"💰 Wallet por defecto: {default_wallet.get_address()}")
            
            if self.enable_network:
                self.network_manager = NetworkManager(self.blockchain, self.host, self.port)
                self.network_manager.start_network()
                print("🌐 Red P2P iniciada")
                
                # Si hay peer, conectarse automáticamente después de 2 seg
                if self.peer:
                    def connect_to_peer():
                        time.sleep(2)
                        try:
                            print(f"🔗 Conectando a peer {self.peer}...")
                            self.network_manager.add_node(self.peer)
                            # También avisar al peer que nos agregue
                            try:
                                requests.post(f"{self.peer}/network/nodes", json={"address": f"http://{self.host}:{self.port}"}, timeout=3)
                                print(f"✅ Conexión bidireccional con {self.peer} establecida")
                            except:
                                print(f"⚠️ Conectado a {self.peer}, pero no se pudo hacer bidireccional (no pasa nada)")
                        except Exception as e:
                            print(f"❌ Error conectando a peer: {e}")
                    threading.Thread(target=connect_to_peer, daemon=True).start()
            
            self.api = BelcoinAPI(self.blockchain, self.wallet_manager)
            if self.network_manager:
                self.api.set_network_manager(self.network_manager)
            
            if self.enable_mining:
                self._start_mining()
            
            self.is_running = True
            
            print("🎉 Nodo iniciado!")
            print(f"📊 Blockchain: {len(self.blockchain.chain)} bloques - Hash génesis: {self.blockchain.chain[0].hash[:16]}...")
            print(f"🔗 API: http://{self.host}:{self.port}")
            print(f"💰 Wallets: {len(self.wallet_manager.wallets)}")
            self._show_node_info()
            
            api_thread = threading.Thread(target=self._run_api)
            api_thread.daemon = True
            api_thread.start()
            
            self._main_loop()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback; traceback.print_exc()
            self.shutdown()
    
    def _start_mining(self):
        try:
            default_wallet = self.wallet_manager.get_wallet()
            if not default_wallet:
                print("⚠️ No hay wallet para minería")
                return
            self.miner = Miner(self.blockchain, default_wallet)
            self.api.set_miner(self.miner)
            self.miner.start_mining()
            print(f"⛏ Minería iniciada: {default_wallet.get_address()}")
        except Exception as e:
            print(f"❌ Error minería: {e}")
    
    def _run_api(self):
        try:
            self.api.run(host=self.host, port=self.port, debug=False)
        except Exception as e:
            print(f"❌ Error API: {e}")
    
    def _main_loop(self):
        print("🔄 Nodo ejecutándose... Ctrl+C para detener")
        try:
            while self.is_running and not self.shutdown_event.is_set():
                if not self.blockchain.is_chain_valid():
                    print("⚠️ Cadena no válida")
                time.sleep(30)
        except KeyboardInterrupt:
            print("\n🛑 Interrupción")
        finally:
            self.shutdown()
    
    def _show_node_info(self):
        print("\n" + "="*50)
        print("📋 INFO NODO")
        print("="*50)
        print(f"🆔 ID: {self.network_manager.node_id if self.network_manager else 'N/A'}")
        print(f"🌐 Host: {self.host}:{self.port}")
        print(f"⛏ Minería: {'✅' if self.enable_mining else '❌'}")
        print(f"🔗 Peer: {self.peer or 'Ninguno'}")
        print(f"💰 Wallet: {self.wallet_manager.get_wallet().get_address() if self.wallet_manager.get_wallet() else 'N/A'}")
        print("="*50 + "\n")
    
    def _signal_handler(self, signum, frame):
        self.shutdown()
    
    def shutdown(self):
        print("🔄 Cerrando...")
        try:
            if self.miner and self.miner.is_mining:
                self.miner.stop_mining()
            if self.network_manager:
                self.network_manager.stop_network()
            self.is_running = False
            self.shutdown_event.set()
            print("✅ Cerrado")
        except Exception as e:
            print(f"❌ Error cierre: {e}")
        finally:
            sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="Nodo Belcoin Multi-Nodo")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--mining", action="store_true", help="Habilitar minería")
    parser.add_argument("--no-network", action="store_true")
    parser.add_argument("--difficulty", type=int, default=4)
    parser.add_argument("--peer", type=str, default=None, help="URL del nodo peer ej: http://localhost:5000")
    
    args = parser.parse_args()
    
    node = BelcoinNode(
        host=args.host,
        port=args.port,
        enable_mining=args.mining,
        enable_network=not args.no_network,
        peer=args.peer
    )
    
    if args.difficulty != 4:
        node.blockchain.difficulty = args.difficulty
    
    node.start()

if __name__ == "__main__":
    main()
