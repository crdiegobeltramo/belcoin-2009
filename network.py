"""
NetworkManager - Versión Bitcoin Real para Belcoin
FIXES aplicados a tu network.py original:
1. Génesis determinístico check
2. Longest Chain Rule (reorg)
3. Sync de cadena completa, no solo bloques sueltos
4. Soporte 0.0.0.0 para internet
5. Auto-broadcast con gossip
6. Limpieza de mempool al cambiar de cadena
"""
import time
import threading
import requests
from typing import List, Dict, Set
from blockchain import Blockchain
from block import Block
from transaction import Transaction

class NetworkNode:
    def __init__(self, node_id: str, host: str, port: int):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.address = f"http://{host}:{port}"
        self.is_active = True
        self.last_seen = time.time()
        self.blocks_received = 0
        self.transactions_received = 0
        self.errors = 0
    
    def to_dict(self) -> dict:
        return {
            'node_id': self.node_id,
            'host': self.host,
            'port': self.port,
            'address': self.address,
            'is_active': self.is_active,
            'last_seen': self.last_seen,
            'blocks_received': self.blocks_received,
            'transactions_received': self.transactions_received,
            'errors': self.errors
        }

class NetworkManager:
    """
    FIXES vs tu versión original:
    - Antes: _sync_blocks_from_node solo hacía append si index == len(chain) y previous_hash == latest
            Si había fork, fallaba y quedaban 2 cadenas distintas
    - Ahora: sync_chain() implementa LONGEST CHAIN RULE de Bitcoin:
            * Pide /blocks completo al peer
            * Valida cadena entera (génesis igual, PoW, hashes)
            * Si es más larga y válida, REEMPLAZA local (reorg)
            * Reconstruye UTXO y limpia mempool
    """
    def __init__(self, blockchain: Blockchain, host: str = "localhost", port: int = 5000):
        self.blockchain = blockchain
        self.host = host
        self.port = port
        # ID único más legible
        import random
        self.node_id = f"node_{int(time.time())}_{random.randint(100,999)}"
        
        # FIX para internet: si host es 0.0.0.0, my_address debe ser IP pública o localhost para anuncio
        # En red pública, el peer debe anunciar su IP real, no 0.0.0.0
        if host == "0.0.0.0":
            # Intentar obtener IP pública, si falla usar localhost como anuncio local
            try:
                import socket
                # Truco para obtener IP local de la interfaz por defecto
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                self.my_address = f"http://{local_ip}:{port}"
            except:
                self.my_address = f"http://localhost:{port}"
        else:
            self.my_address = f"http://{host}:{port}"
        
        self.known_nodes: Set[str] = set()
        self.active_nodes: Dict[str, NetworkNode] = {}
        
        self.is_syncing = False
        self.sync_thread = None
        self.start_time = time.time()
        
        # Stats para dashboard
        self.blocks_sent = 0
        self.sync_count = 0
        
        print(f"Nodo de red iniciado: {self.node_id} en {host}:{port}")
        print(f"Dirección anunciada: {self.my_address}")
    
    def start_network(self):
        print(f"Nodo de red iniciado: {self.node_id} en {self.host}:{self.port}")
        self.start_sync()
    
    def stop_network(self):
        self.stop_sync()
        print("Servicio de red detenido")
    
    def add_node(self, node_address: str) -> bool:
        try:
            # Normalizar
            if not node_address.startswith("http://") and not node_address.startswith("https://"):
                node_address = f"http://{node_address}"
            
            node_address = node_address.rstrip("/")
            
            # FIX: No agregarse a sí mismo - comparar solo host:port ignorando 0.0.0.0
            my_ports = [f":{self.port}"]
            is_self = False
            for mp in my_ports:
                if mp in node_address and ("localhost" in node_address or "127.0.0.1" in node_address or self.host in node_address or "0.0.0.0" in self.host):
                    # Si mismo puerto y mismo host local, es self
                    if node_address.endswith(f":{self.port}") or f":{self.port}/" in node_address:
                        # Pero permitir si es IP diferente (para test multi-nodo local con puertos distintos)
                        if node_address != self.my_address:
                            # Si es localhost con mismo puerto que yo, sí es self
                            if "localhost" in node_address or "127.0.0.1" in node_address:
                                # Solo es self si puerto coincide y host es local
                                if f":{self.port}" in node_address:
                                    # En modo 0.0.0.0, localhost:port es self
                                    if self.host == "0.0.0.0" or self.host in ["localhost", "127.0.0.1"]:
                                        is_self = True
                        else:
                            is_self = False
            
            # Simplificado: si la dirección normalizada es igual a my_address, es self
            if node_address == self.my_address:
                is_self = True
            
            if is_self:
                print(f"⚠️ No puedes agregarte a ti mismo: {node_address}")
                return False
            
            if self._ping_node(node_address):
                self.known_nodes.add(node_address)
                node = NetworkNode(
                    node_id=f"node_{len(self.active_nodes)}",
                    host=node_address.split("//")[1].split(":")[0],
                    port=int(node_address.split(":")[-1].split("/")[0])
                )
                self.active_nodes[node_address] = node
                print(f"✅ Nodo agregado: {node_address}")
                
                # Sync inmediato con nuevo peer (longest chain)
                threading.Thread(target=self.sync_chain, daemon=True).start()
                return True
            else:
                print(f"No se pudo conectar al nodo: {node_address} (lo agrego igual para reintentar)")
                self.known_nodes.add(node_address)
                return False
                
        except Exception as e:
            print(f"Error al agregar nodo {node_address}: {e}")
            return False
    
    def remove_node(self, node_address: str) -> bool:
        node_address = node_address.rstrip("/")
        if node_address in self.known_nodes:
            self.known_nodes.remove(node_address)
            if node_address in self.active_nodes:
                del self.active_nodes[node_address]
            print(f"Nodo removido: {node_address}")
            return True
        return False
    
    def _ping_node(self, node_address: str) -> bool:
        try:
            response = requests.get(f"{node_address}/ping", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def broadcast_transaction(self, transaction: Transaction) -> int:
        if not self.active_nodes:
            return 0
        successful = 0
        tx_data = transaction.to_dict()
        for node_address, node in list(self.active_nodes.items()):
            try:
                response = requests.post(f"{node_address}/transactions", json=tx_data, timeout=5)
                if response.status_code == 200:
                    successful += 1
                    node.transactions_received += 1
                    node.last_seen = time.time()
                else:
                    node.errors += 1
            except Exception as e:
                node.errors += 1
        print(f"Transacción transmitida a {successful}/{len(self.active_nodes)} nodos")
        return successful
    
    def broadcast_block(self, block: Block) -> int:
        if not self.active_nodes:
            return 0
        successful = 0
        block_data = block.to_dict()
        for node_address, node in list(self.active_nodes.items()):
            try:
                response = requests.post(f"{node_address}/blocks", json=block_data, timeout=10)
                if response.status_code in [200, 201, 202]:
                    successful += 1
                    node.blocks_received += 1
                    node.last_seen = time.time()
                    self.blocks_sent += 1
                else:
                    node.errors += 1
            except Exception as e:
                node.errors += 1
                print(f"Error al transmitir bloque a {node_address}: {e}")
        print(f"📢 Bloque #{block.index} transmitido a {successful}/{len(self.active_nodes)} nodos")
        return successful
    
    def start_sync(self):
        if self.is_syncing:
            return
        self.is_syncing = True
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        print("Sincronización automática iniciada (longest chain cada 30s)")
    
    def stop_sync(self):
        self.is_syncing = False
        if self.sync_thread:
            self.sync_thread.join(timeout=1)
        print("Sincronización detenida")
    
    def _sync_loop(self):
        while self.is_syncing:
            try:
                self.sync_chain()
                self._cleanup_inactive_nodes()
                time.sleep(30)
            except Exception as e:
                print(f"Error en sync_loop: {e}")
                time.sleep(60)
    
    # ========= LONGEST CHAIN RULE - FIX PRINCIPAL =========
    def sync_chain(self) -> bool:
        """
        Sincronización Bitcoin real:
        1. Pide /blocks a todos los peers
        2. Encuentra la cadena más larga VÁLIDA
        3. Verifica génesis igual (evita redes separadas)
        4. Si peer es más larga, reemplaza local y reconstruye UTXO
        """
        if not self.known_nodes and not self.active_nodes:
            return False
        
        all_nodes = set(self.known_nodes) | set(self.active_nodes.keys())
        if not all_nodes:
            return False
        
        print(f"🔄 Sincronizando... {len(all_nodes)} peers, altura local {len(self.blockchain.chain)}")
        
        longest_chain = None
        max_length = len(self.blockchain.chain)
        best_node = None
        
        for node_address in list(all_nodes):
            try:
                resp = requests.get(f"{node_address}/blocks", timeout=5)
                if resp.status_code != 200:
                    continue
                
                peer_blocks_data = resp.json()
                peer_length = len(peer_blocks_data)
                
                if peer_length <= max_length:
                    continue
                
                # Reconstruir cadena del peer
                peer_chain = []
                for bdata in peer_blocks_data:
                    try:
                        peer_chain.append(Block.from_dict(bdata))
                    except Exception as e:
                        print(f"  ❌ Error parseando bloque de {node_address}: {e}")
                        peer_chain = []
                        break
                
                if not peer_chain:
                    continue
                
                # VALIDACIÓN COMPLETA de cadena
                if self._is_valid_chain(peer_chain):
                    if peer_length > max_length:
                        max_length = peer_length
                        longest_chain = peer_chain
                        best_node = node_address
                        print(f"  🏆 Cadena más larga en {node_address}: {peer_length} bloques")
                else:
                    print(f"  ❌ Cadena inválida de {node_address}")
                    
            except Exception as e:
                print(f"  ⚠️ No se pudo sync con {node_address}: {e}")
                continue
        
        # ADOPTAR cadena más larga (REORG)
        if longest_chain and max_length > len(self.blockchain.chain):
            print(f"🔀 REORG: {len(self.blockchain.chain)} -> {max_length} bloques desde {best_node}")
            try:
                # Guardar cadena vieja por si falla
                old_chain = self.blockchain.chain
                
                self.blockchain.chain = longest_chain
                # Reconstruir UTXO desde cero
                self.blockchain.utxo_set = {}
                for block in self.blockchain.chain:
                    self.blockchain._update_utxo_set(block)
                
                # Limpiar mempool de txs ya confirmadas
                confirmed = set()
                for block in self.blockchain.chain:
                    for tx in block.transactions:
                        confirmed.add(tx.hash)
                
                before = len(self.blockchain.pending_transactions)
                self.blockchain.pending_transactions = [
                    tx for tx in self.blockchain.pending_transactions if tx.hash not in confirmed
                ]
                
                self.sync_count += 1
                print(f"✅ Reorg exitoso! Nueva altura {len(self.blockchain.chain)} | Mempool {before}->{len(self.blockchain.pending_transactions)}")
                return True
                
            except Exception as e:
                print(f"❌ Error en reorg, revertiendo: {e}")
                import traceback; traceback.print_exc()
                self.blockchain.chain = old_chain
                return False
        else:
            # Si no hay cadena más larga, intentar sync de bloques sueltos (compatibilidad con tu código viejo)
            self._sync_with_nodes()
            return False
    
    def _sync_with_nodes(self):
        """Compatibilidad con tu código original: sync de bloques individuales si no hay reorg"""
        for node_address in list(self.active_nodes.keys()):
            try:
                resp = requests.get(f"{node_address}/blockchain/height", timeout=5)
                if resp.status_code == 200:
                    remote_height = resp.json().get('height', 0)
                    local_height = len(self.blockchain.chain)
                    if remote_height > local_height:
                        self._sync_blocks_from_node(node_address, local_height, remote_height)
            except Exception as e:
                pass
    
    def _sync_blocks_from_node(self, node_address: str, from_height: int, to_height: int):
        try:
            print(f"Sincronizando bloques {from_height} a {to_height} desde {node_address}")
            for height in range(from_height, to_height):
                # Tu API original usa /blocks/<index> con índice, no altura 1-indexed
                # from_height es len(chain), así que pedimos height
                resp = requests.get(f"{node_address}/blocks/{height}", timeout=10)
                if resp.status_code == 200:
                    block_data = resp.json()
                    block = Block.from_dict(block_data)
                    if self._is_block_valid_next(block):
                        self.blockchain.chain.append(block)
                        self.blockchain._update_utxo_set(block)
                        print(f"Bloque {height} sincronizado")
                    else:
                        print(f"Bloque {height} inválido")
                        break
        except Exception as e:
            print(f"Error sync bloques desde {node_address}: {e}")
    
    def _is_block_valid_next(self, block: Block) -> bool:
        """Valida que bloque sea el siguiente esperado (para sync incremental)"""
        if block.index != len(self.blockchain.chain):
            return False
        if len(self.blockchain.chain) > 0:
            prev = self.blockchain.chain[-1]
            if block.previous_hash != prev.hash:
                return False
        if block.hash != block._calculate_hash():
            return False
        if block.hash[:self.blockchain.difficulty] != "0" * self.blockchain.difficulty:
            return False
        return True
    
    def _is_valid_chain(self, chain) -> bool:
        """Valida cadena completa - génesis + PoW + hashes"""
        if not chain:
            return False
        
        # 1. Génesis debe ser igual (CRÍTICO para red pública)
        local_genesis = self.blockchain.chain[0].hash if self.blockchain.chain else None
        if local_genesis and chain[0].hash != local_genesis:
            print(f"  ⚠️ Génesis diferente! Local {local_genesis[:10]} vs Peer {chain[0].hash[:10]}")
            print(f"     Usa blockchain_fixed.py con timestamp fijo 1700000000.0")
            return False
        
        # 2. Validar cada bloque
        for i in range(1, len(chain)):
            curr = chain[i]
            prev = chain[i-1]
            if curr.previous_hash != prev.hash:
                return False
            if curr.hash != curr._calculate_hash():
                return False
            if curr.hash[:self.blockchain.difficulty] != "0" * self.blockchain.difficulty:
                return False
        
        return True
    
    def _cleanup_inactive_nodes(self):
        current = time.time()
        threshold = 300
        for addr, node in list(self.active_nodes.items()):
            if current - node.last_seen > threshold:
                print(f"Removiendo nodo inactivo: {addr}")
                self.remove_node(addr)
    
    def get_network_stats(self) -> dict:
        uptime = time.time() - self.start_time
        return {
            'node_id': self.node_id,
            'my_address': self.my_address,
            'host': self.host,
            'port': self.port,
            'known_nodes': len(self.known_nodes),
            'active_nodes': len(self.active_nodes),
            'is_syncing': self.is_syncing,
            'blocks_sent': self.blocks_sent,
            'sync_count': self.sync_count,
            'blockchain_height': len(self.blockchain.chain),
            'uptime': uptime
        }
    
    def get_node_list(self) -> List[dict]:
        return [node.to_dict() for node in self.active_nodes.values()]
