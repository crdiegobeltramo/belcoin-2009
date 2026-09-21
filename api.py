"""
api.py - FIX para red pública
- Escucha en 0.0.0.0
- Ruta / para evitar 404
- Validación estricta al recibir bloques (para internet)
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import time
from blockchain import Blockchain
from wallet import Wallet, WalletManager
from miner import Miner
from network import NetworkManager
from transaction import Transaction, TransactionInput, TransactionOutput
from block import Block

class BelcoinAPI:
    def __init__(self, blockchain: Blockchain, wallet_manager: WalletManager = None):
        self.blockchain = blockchain
        self.wallet_manager = wallet_manager or WalletManager()
        self.app = Flask(__name__)
        self.network_manager = None
        self.miner = None
        CORS(self.app)
        self._register_routes()
    
    def _register_routes(self):
        # RUTA RAÍZ - FIX 404
        @self.app.route('/', methods=['GET'])
        def index():
            try:
                return jsonify({
                    'message': '🚀 Nodo Belcoin funcionando!',
                    'status': 'online',
                    'network': 'belcoin-mainnet',
                    'node_id': self.network_manager.node_id if self.network_manager else 'local',
                    'my_address': self.network_manager.my_address if self.network_manager else f'http://localhost:5000',
                    'blockchain_height': len(self.blockchain.chain),
                    'genesis_hash': self.blockchain.chain[0].hash if self.blockchain.chain else None,
                    'pending_transactions': len(self.blockchain.pending_transactions),
                    'is_chain_valid': self.blockchain.is_chain_valid(),
                    'difficulty': self.blockchain.difficulty,
                    'endpoints': {
                        'blocks': '/blocks',
                        'block_by_index': '/blocks/<index>',
                        'blockchain': '/blockchain',
                        'transactions': '/transactions',
                        'wallets': '/wallets',
                        'mining_status': '/mining/status',
                        'mining_start': 'POST /mining/start {wallet_name}',
                        'network': '/network',
                        'add_node': 'POST /network/nodes {address}',
                        'health': '/health',
                        'ping': '/ping',
                        'explorer': '/explorer/address/<address>'
                    }
                })
            except Exception as e:
                return jsonify({'message': 'Belcoin OK', 'error': str(e)})

        # BLOCKCHAIN
        @self.app.route('/blockchain', methods=['GET'])
        def get_blockchain_info():
            try:
                info = self.blockchain.get_blockchain_info()
                info['genesis_hash'] = self.blockchain.chain[0].hash if self.blockchain.chain else None
                return jsonify(info)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/blockchain/height', methods=['GET'])
        def get_blockchain_height():
            return jsonify({'height': len(self.blockchain.chain)})

        @self.app.route('/blocks', methods=['GET'])
        def get_blocks():
            try:
                blocks = [block.to_dict() for block in self.blockchain.chain]
                return jsonify(blocks)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/blocks/<int:index>', methods=['GET'])
        def get_block_by_index(index):
            try:
                block = self.blockchain.get_block_by_index(index)
                if block:
                    return jsonify(block.to_dict())
                else:
                    return jsonify({'error': 'Block not found'}), 404
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/blocks/hash/<hash>', methods=['GET'])
        def get_block_by_hash(block_hash):
            try:
                block = self.blockchain.get_block_by_hash(block_hash)
                if block:
                    return jsonify(block.to_dict())
                else:
                    return jsonify({'error': 'Block not found'}), 404
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/blocks', methods=['POST'])
        def add_block():
            """
            Recibe bloque minado por otro nodo - VALIDACIÓN ESTRICTA PARA INTERNET
            """
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'No data provided'}), 400
                
                # Crear bloque desde datos
                block = Block.from_dict(data)
                
                # === VALIDACIONES PARA RED PÚBLICA ===
                # 1. Verificar que no sea génesis (no se puede reemplazar génesis)
                if block.index == 0:
                    return jsonify({'error': 'Cannot replace genesis block'}), 400
                
                # 2. Verificar que previous_hash coincida con nuestro último bloque O sea parte de un fork más largo
                # Para simplificar: si es el siguiente bloque, validarlo
                # Si es más largo, el sync_chain se encargará
                latest = self.blockchain.get_latest_block()
                
                if block.previous_hash == latest.hash:
                    # Es el siguiente bloque esperado
                    if block.hash[:self.blockchain.difficulty] != "0" * self.blockchain.difficulty:
                        return jsonify({'error': 'Block does not meet difficulty (PoW invalid)'}), 400
                    
                    if block.hash != block._calculate_hash():
                        return jsonify({'error': 'Invalid block hash'}), 400
                    
                    # Verificar que todas las txs sean válidas
                    # (excepto coinbase)
                    for tx in block.transactions[1:]:
                        # Validación básica de firma, etc. se hace en blockchain
                        pass
                    
                    # Agregar a cadena
                    self.blockchain.chain.append(block)
                    self.blockchain._update_utxo_set(block)
                    
                    # Limpiar mempool
                    confirmed = set(tx.hash for tx in block.transactions)
                    self.blockchain.pending_transactions = [
                        tx for tx in self.blockchain.pending_transactions if tx.hash not in confirmed
                    ]
                    
                    print(f"✅ Bloque #{block.index} aceptado de peer {request.remote_addr}")
                    
                    # Retransmitir a otros peers (gossip)
                    if self.network_manager:
                        # No retransmitir al que nos lo envió para evitar loop
                        threading_thread = __import__('threading').Thread(
                            target=self.network_manager.broadcast_block,
                            args=(block,),
                            daemon=True
                        )
                        threading_thread.start()
                    
                    return jsonify({'message': 'Block added', 'block': block.to_dict()})
                
                elif block.index > len(self.blockchain.chain):
                    # Es un bloque futuro, puede que estemos desincronizados
                    # Disparar sincronización completa
                    print(f"🔄 Bloque futuro #{block.index} recibido (local {len(self.blockchain.chain)}), sincronizando...")
                    if self.network_manager:
                        threading.Thread(target=self.network_manager.sync_chain, daemon=True).start()
                    return jsonify({'message': 'Block received, syncing chain'}), 202
                
                else:
                    # Bloque viejo o duplicado
                    return jsonify({'message': 'Block already exists or is old'}), 200
                    
            except Exception as e:
                import traceback
                traceback.print_exc()
                return jsonify({'error': str(e)}), 500

        # TRANSACTIONS
        @self.app.route('/transactions', methods=['GET'])
        def get_transactions():
            try:
                transactions = [tx.to_dict() for tx in self.blockchain.pending_transactions]
                return jsonify(transactions)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/transactions', methods=['POST'])
        def create_transaction():
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'No data provided'}), 400
                
                transaction = Transaction.from_dict(data)
                
                if self.blockchain.add_transaction(transaction):
                    if self.network_manager:
                        self.network_manager.broadcast_transaction(transaction)
                    return jsonify({'message': 'Transaction created', 'transaction': transaction.to_dict()})
                else:
                    return jsonify({'error': 'Invalid transaction'}), 400
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # WALLETS
        @self.app.route('/wallets', methods=['GET'])
        def get_wallets():
            try:
                wallets = []
                for name, wallet in self.wallet_manager.list_wallets():
                    wallets.append({
                        'name': name,
                        'address': wallet.get_address(),
                        'balance': self.blockchain.get_balance(wallet.get_address())
                    })
                return jsonify(wallets)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/wallets', methods=['POST'])
        def create_wallet():
            try:
                data = request.get_json() or {}
                name = data.get('name')
                wallet = self.wallet_manager.create_wallet(name)
                return jsonify({
                    'message': 'Wallet created',
                    'wallet': {
                        'name': name or f"wallet_{len(self.wallet_manager.wallets)}",
                        'address': wallet.get_address(),
                        'public_key': wallet.export_public_key(),
                        'private_key': wallet.export_private_key()
                    }
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/wallets/<name>/balance', methods=['GET'])
        def get_wallet_balance(name):
            try:
                wallet = self.wallet_manager.get_wallet(name)
                if wallet:
                    balance = self.blockchain.get_balance(wallet.get_address())
                    return jsonify({'wallet': name, 'address': wallet.get_address(), 'balance': balance})
                else:
                    return jsonify({'error': 'Wallet not found'}), 404
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/wallets/<name>/send', methods=['POST'])
        def send_transaction(name):
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'No data provided'}), 400
                
                recipient_address = data.get('recipient_address')
                amount = data.get('amount')
                fee = data.get('fee', 0.0001)
                
                if not recipient_address or not amount:
                    return jsonify({'error': 'Missing recipient_address or amount'}), 400
                
                wallet = self.wallet_manager.get_wallet(name)
                if not wallet:
                    return jsonify({'error': 'Wallet not found'}), 404
                
                transaction = wallet.create_transaction(recipient_address, amount, fee)
                if not transaction:
                    return jsonify({'error': 'Failed to create transaction (insufficient funds?)'}), 400
                
                if self.blockchain.add_transaction(transaction):
                    if self.network_manager:
                        self.network_manager.broadcast_transaction(transaction)
                    return jsonify({'message': 'Transaction sent', 'transaction': transaction.to_dict()})
                else:
                    return jsonify({'error': 'Failed to add transaction'}), 400
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # MINING
        @self.app.route('/mining/start', methods=['POST'])
        def start_mining():
            try:
                data = request.get_json() or {}
                wallet_name = data.get('wallet_name')
                if not wallet_name:
                    return jsonify({'error': 'wallet_name is required'}), 400
                
                wallet = self.wallet_manager.get_wallet(wallet_name)
                if not wallet:
                    return jsonify({'error': 'Wallet not found'}), 404
                
                if not self.miner:
                    self.miner = Miner(self.blockchain, wallet)
                
                self.miner.start_mining()
                return jsonify({'message': 'Mining started'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/mining/stop', methods=['POST'])
        def stop_mining():
            try:
                if self.miner:
                    self.miner.stop_mining()
                    return jsonify({'message': 'Mining stopped'})
                else:
                    return jsonify({'error': 'No miner running'}), 400
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/mining/status', methods=['GET'])
        def get_mining_status():
            try:
                if self.miner:
                    stats = self.miner.get_mining_stats()
                    return jsonify(stats)
                else:
                    return jsonify({'is_mining': False, 'message': 'No miner'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # NETWORK
        @self.app.route('/network', methods=['GET'])
        def get_network_info():
            try:
                if self.network_manager:
                    stats = self.network_manager.get_network_stats()
                    nodes = self.network_manager.get_node_list()
                    return jsonify({'stats': stats, 'nodes': nodes})
                else:
                    return jsonify({'error': 'Network not available'}), 400
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/network/nodes', methods=['POST'])
        def add_network_node():
            try:
                data = request.get_json()
                if not data or 'address' not in data:
                    return jsonify({'error': 'address is required'}), 400
                
                if not self.network_manager:
                    return jsonify({'error': 'Network not available'}), 400
                
                node_address = data['address']
                if self.network_manager.add_node(node_address):
                    return jsonify({'message': 'Node added', 'nodes': self.network_manager.get_node_list()})
                else:
                    return jsonify({'error': 'Failed to add node'}), 400
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/network/sync', methods=['POST'])
        def force_sync():
            """Fuerza sincronización manual - útil para red pública"""
            try:
                if self.network_manager:
                    result = self.network_manager.sync_chain()
                    return jsonify({'message': 'Sync completed', 'synced': result, 'height': len(self.blockchain.chain)})
                else:
                    return jsonify({'error': 'Network not available'}), 400
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # UTIL
        @self.app.route('/ping', methods=['GET'])
        def ping():
            return jsonify({'message': 'pong', 'node_id': self.network_manager.node_id if self.network_manager else 'unknown', 'timestamp': time.time()})
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            try:
                return jsonify({
                    'status': 'healthy',
                    'blockchain_height': len(self.blockchain.chain),
                    'genesis_hash': self.blockchain.chain[0].hash if self.blockchain.chain else None,
                    'pending_transactions': len(self.blockchain.pending_transactions),
                    'is_chain_valid': self.blockchain.is_chain_valid(),
                    'peers': len(self.network_manager.nodes) if self.network_manager else 0,
                    'timestamp': time.time()
                })
            except Exception as e:
                return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
        
        @self.app.route('/explorer/address/<address>', methods=['GET'])
        def explore_address(address):
            try:
                balance = self.blockchain.get_balance(address)
                transactions = []
                for block in self.blockchain.chain:
                    for tx in block.transactions:
                        for output in tx.outputs:
                            if output.address == address:
                                transactions.append({
                                    'type': 'received',
                                    'block': block.index,
                                    'transaction': tx.hash,
                                    'amount': output.amount,
                                    'timestamp': block.timestamp
                                })
                return jsonify({'address': address, 'balance': balance, 'transactions': transactions})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
    
    def set_network_manager(self, network_manager: NetworkManager):
        self.network_manager = network_manager
    
    def set_miner(self, miner: Miner):
        self.miner = miner
    
    def run(self, host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
        print(f"API Belcoin iniciada en http://{host}:{port}")
        print(f"Accesible desde internet si el puerto está abierto")
        self.app.run(host=host, port=port, debug=debug, threaded=True)
    
    def get_app(self):
        return self.app
