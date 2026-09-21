import hashlib
import json
import time
from typing import List, Dict, Optional, Tuple
from block import Block
from transaction import Transaction, TransactionInput, TransactionOutput
from wallet import Wallet

class Blockchain:
    """
    Clase principal que implementa la blockchain de Belcoin.
    Sigue las mismas reglas y parámetros que Bitcoin.
    """
    
    def __init__(self):
        # Parámetros de Bitcoin
        self.BLOCK_TIME_TARGET = 600  # 10 minutos en segundos
        self.DIFFICULTY_ADJUSTMENT_INTERVAL = 2016  # Bloques entre ajustes de dificultad
        self.BLOCK_REWARD = 50.0  # Recompensa inicial por bloque
        self.HALVING_INTERVAL = 210000  # Bloques entre halvings
        self.MAX_BLOCK_SIZE = 1024 * 1024  # 1MB en bytes
        
        # Estado de la blockchain
        self.chain = []
        self.pending_transactions = []
        self.difficulty = 4  # Dificultad inicial (número de ceros al inicio)
        self.utxo_set = {}  # Conjunto de UTXOs no gastados
        self.wallets = {}  # Wallets registrados
        
        # Estadísticas
        self.total_transactions = 0
        self.total_blocks_mined = 0
        self.start_time = time.time()
        
        # Crear bloque génesis
        self._create_genesis_block()
    
    def _create_genesis_block(self):
        """Crea el bloque génesis DETERMINÍSTICO para que todos los nodos compartan el mismo génesis."""
        genesis_transaction = Transaction.create_coinbase(
            miner_address="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            amount=self.BLOCK_REWARD,
            block_height=0
        )
        
        # FIX: timestamp fijo para que el hash génesis sea igual en todos los nodos
        fixed_timestamp = 1700000000.0  # 14 Nov 2023 fijo
        
        genesis_block = Block(
            index=0,
            transactions=[genesis_transaction],
            timestamp=fixed_timestamp,
            previous_hash="0" * 64,
            nonce=0
        )
        
        # Minar el bloque génesis con dificultad fija
        genesis_block.mine_block(self.difficulty)
        
        self.chain.append(genesis_block)
        self._update_utxo_set(genesis_block)
        
        print(f"Bloque génesis creado (determinístico): {genesis_block}")
    
    def get_latest_block(self) -> Block:
        """Retorna el último bloque de la cadena."""
        return self.chain[-1] if self.chain else None
    
    def get_block_by_hash(self, block_hash: str) -> Optional[Block]:
        """Obtiene un bloque por su hash."""
        for block in self.chain:
            if block.hash == block_hash:
                return block
        return None
    
    def get_block_by_index(self, index: int) -> Optional[Block]:
        """Obtiene un bloque por su índice."""
        if 0 <= index < len(self.chain):
            return self.chain[index]
        return None
    
    def add_transaction(self, transaction: Transaction) -> bool:
        """
        Agrega una transacción al mempool.
        Retorna True si la transacción es válida y se agregó.
        """
        if not self._is_transaction_valid(transaction):
            print("Transacción inválida")
            return False
        
        # Verificar que no esté duplicada
        if any(tx.hash == transaction.hash for tx in self.pending_transactions):
            print("Transacción ya existe en el mempool")
            return False
        
        self.pending_transactions.append(transaction)
        self.total_transactions += 1
        print(f"Transacción agregada al mempool: {transaction.hash[:10]}...")
        return True
    
    def _is_transaction_valid(self, transaction: Transaction) -> bool:
        """Verifica si una transacción es válida."""
        # Verificar que no sea coinbase
        if transaction.is_coinbase():
            return False
        
        # Verificar firma
        if not transaction.verify_signature():
            print("Firma de transacción inválida")
            return False
        
        # Verificar que las entradas existan en el UTXO set
        for input_tx in transaction.inputs:
            utxo_key = f"{input_tx.tx_hash}:{input_tx.output_index}"
            if utxo_key not in self.utxo_set:
                print(f"UTXO no encontrado: {utxo_key}")
                return False
        
        # Verificar que el remitente tenga suficientes fondos
        total_input = 0
        for input_tx in transaction.inputs:
            utxo_key = f"{input_tx.tx_hash}:{input_tx.output_index}"
            total_input += self.utxo_set[utxo_key]['amount']
        
        total_output = sum(output.amount for output in transaction.outputs)
        
        if total_input < total_output:
            print(f"Fondos insuficientes. Entrada: {total_input}, Salida: {total_output}")
            return False
        
        return True
    
    def mine_block(self, miner_address: str) -> Optional[Block]:
        """
        Mina un nuevo bloque con las transacciones pendientes.
        Retorna el bloque minado si es exitoso.
        """
        if not self.pending_transactions:
            print("No hay transacciones pendientes para minar")
            return None
        
        # Crear transacción coinbase para el minero
        block_reward = self._calculate_block_reward()
        coinbase_tx = Transaction.create_coinbase(
            miner_address=miner_address,
            amount=block_reward,
            block_height=len(self.chain)
        )
        
        # Seleccionar transacciones para el bloque (límite de tamaño)
        selected_transactions = self._select_transactions_for_block()
        
        # Crear el nuevo bloque
        previous_block = self.get_latest_block()
        new_block = Block(
            index=len(self.chain),
            transactions=[coinbase_tx] + selected_transactions,
            timestamp=time.time(),
            previous_hash=previous_block.hash,
            nonce=0
        )
        
        # Minar el bloque
        print(f"Minando bloque #{new_block.index} con dificultad {self.difficulty}...")
        start_time = time.time()
        
        if new_block.mine_block(self.difficulty):
            mining_time = time.time() - start_time
            print(f"Bloque minado en {mining_time:.2f} segundos")
            
            # Agregar el bloque a la cadena
            self.chain.append(new_block)
            
            # Actualizar UTXO set
            self._update_utxo_set(new_block)
            
            # Remover transacciones minadas del mempool
            for tx in selected_transactions:
                self.pending_transactions.remove(tx)
            
            # Ajustar dificultad si es necesario
            self._adjust_difficulty()
            
            self.total_blocks_mined += 1
            return new_block
        else:
            print("Error al minar el bloque")
            return None
    
    def _select_transactions_for_block(self) -> List[Transaction]:
        """Selecciona transacciones para incluir en el bloque (por tamaño y tarifa)."""
        # Ordenar por tarifa (mayor a menor)
        sorted_transactions = sorted(
            self.pending_transactions,
            key=lambda tx: tx.fee,
            reverse=True
        )
        
        selected = []
        current_size = 0
        
        for tx in sorted_transactions:
            tx_size = len(json.dumps(tx.to_dict()))
            if current_size + tx_size <= self.MAX_BLOCK_SIZE:
                selected.append(tx)
                current_size += tx_size
            else:
                break
        
        return selected
    
    def _calculate_block_reward(self) -> float:
        """Calcula la recompensa del bloque actual (considerando halving)."""
        current_height = len(self.chain)
        halvings = current_height // self.HALVING_INTERVAL
        return self.BLOCK_REWARD / (2 ** halvings)
    
    def _update_utxo_set(self, block: Block):
        """Actualiza el conjunto de UTXOs después de agregar un bloque."""
        # Agregar nuevas salidas
        for tx in block.transactions:
            for i, output in enumerate(tx.outputs):
                utxo_key = f"{tx.hash}:{i}"
                self.utxo_set[utxo_key] = {
                    'address': output.address,
                    'amount': output.amount,
                    'tx_hash': tx.hash,
                    'output_index': i
                }
        
        # Remover entradas gastadas
        for tx in block.transactions:
            if not tx.is_coinbase():
                for input_tx in tx.inputs:
                    utxo_key = f"{input_tx.tx_hash}:{input_tx.output_index}"
                    if utxo_key in self.utxo_set:
                        del self.utxo_set[utxo_key]
    
    def _adjust_difficulty(self):
        """Ajusta la dificultad de minería según el tiempo objetivo."""
        if len(self.chain) % self.DIFFICULTY_ADJUSTMENT_INTERVAL != 0:
            return
        
        # Calcular tiempo promedio de los últimos 2016 bloques
        start_block = self.chain[-self.DIFFICULTY_ADJUSTMENT_INTERVAL]
        end_block = self.chain[-1]
        
        time_diff = end_block.timestamp - start_block.timestamp
        expected_time = self.BLOCK_TIME_TARGET * self.DIFFICULTY_ADJUSTMENT_INTERVAL
        
        # Ajustar dificultad
        if time_diff < expected_time / 4:
            self.difficulty += 1
        elif time_diff > expected_time * 4:
            self.difficulty = max(1, self.difficulty - 1)
        
        print(f"Dificultad ajustada a: {self.difficulty}")
    
    def get_balance(self, address: str) -> float:
        """Obtiene el balance de una dirección."""
        balance = 0.0
        for utxo_key, utxo in self.utxo_set.items():
            if utxo['address'] == address:
                balance += utxo['amount']
        return balance
    
    def is_chain_valid(self) -> bool:
        """Verifica que toda la cadena de bloques sea válida."""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]
            
            # Verificar hash del bloque anterior
            if current_block.previous_hash != previous_block.hash:
                print(f"Hash del bloque anterior inválido en bloque {i}")
                return False
            
            # Verificar hash del bloque actual
            if current_block.hash != current_block._calculate_hash():
                print(f"Hash del bloque {i} inválido")
                return False
            
            # Verificar que el bloque cumpla con la dificultad
            if current_block.hash[:self.difficulty] != "0" * self.difficulty:
                print(f"Bloque {i} no cumple con la dificultad")
                return False
        
        return True
    
    def get_blockchain_info(self) -> dict:
        """Retorna información general de la blockchain."""
        return {
            'total_blocks': len(self.chain),
            'total_transactions': self.total_transactions,
            'pending_transactions': len(self.pending_transactions),
            'difficulty': self.difficulty,
            'block_reward': self._calculate_block_reward(),
            'utxo_count': len(self.utxo_set),
            'uptime': time.time() - self.start_time
        }
    
    def to_dict(self) -> dict:
        """Convierte la blockchain a un diccionario para serialización."""
        return {
            'chain': [block.to_dict() for block in self.chain],
            'pending_transactions': [tx.to_dict() for tx in self.pending_transactions],
            'difficulty': self.difficulty,
            'utxo_set': self.utxo_set,
            'total_transactions': self.total_transactions,
            'total_blocks_mined': self.total_blocks_mined,
            'start_time': self.start_time
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Blockchain':
        """Crea una blockchain desde un diccionario."""
        blockchain = cls()
        
        # Restaurar cadena de bloques
        blockchain.chain = [Block.from_dict(block_data) for block_data in data['chain']]
        
        # Restaurar transacciones pendientes
        blockchain.pending_transactions = [
            Transaction.from_dict(tx_data) for tx_data in data['pending_transactions']
        ]
        
        # Restaurar otros datos
        blockchain.difficulty = data['difficulty']
        blockchain.utxo_set = data['utxo_set']
        blockchain.total_transactions = data['total_transactions']
        blockchain.total_blocks_mined = data['total_blocks_mined']
        blockchain.start_time = data['start_time']
        
        return blockchain
    
    def __str__(self) -> str:
        return f"Belcoin Blockchain - {len(self.chain)} bloques - Dificultad: {self.difficulty}"
    
    def __repr__(self) -> str:
        return self.__str__()
