import hashlib
import time
import json
import threading

class Miner:
    def __init__(self, blockchain, wallet_address, difficulty=None):
        # wallet_address puede ser WalletManager o string
        if hasattr(wallet_address, 'get_address'):
            self.wallet_str = wallet_address.get_address()
        else:
            self.wallet_str = str(wallet_address)
        self.blockchain = blockchain
        self.difficulty = difficulty or getattr(blockchain, 'difficulty', 4)
        self.running = False
        self.blocks_mined = 0
        self.hashes = 0
        self._thread = None

    def _mine_one(self):
        from block import Block
        from transaction import Transaction
        # Crear coinbase que te paga a VOS
        try:
            # Intenta el factory, si falla crea manual
            if hasattr(Transaction, 'create_coinbase'):
                coinbase = Transaction.create_coinbase(self.wallet_str, 50)
            else:
                raise Exception("no factory")
        except:
            # Transacción manual compatible con tu transaction.py
            coinbase = Transaction(
                inputs=[],
                outputs=[{'address': self.wallet_str, 'amount': 50}],
                timestamp=time.time()
            )

        # Crear bloque
        prev = self.blockchain.chain[-1]
        new_block = self.blockchain.create_block([coinbase]) if hasattr(self.blockchain, 'create_block') else None
        if new_block is None:
            # Fallback manual
            from block import Block
            new_block = Block(
                index=len(self.blockchain.chain),
                previous_hash=prev.hash,
                transactions=[coinbase],
                timestamp=time.time(),
                nonce=0
            )

        target = "0" * self.difficulty
        nonce = 0
        while self.running:
            new_block.nonce = nonce
            # calcular hash de forma robusta
            try:
                h = new_block.calculate_hash()
            except:
                # fallback hash
                data = f"{new_block.index}{new_block.previous_hash}{new_block.timestamp}{nonce}{self.wallet_str}"
                h = hashlib.sha256(data.encode()).hexdigest()
                new_block.hash = h

            self.hashes += 1
            if h.startswith(target):
                new_block.hash = h
                # Intentar agregar
                try:
                    added = self.blockchain.add_block(new_block)
                except:
                    # fallback add directo
                    self.blockchain.chain.append(new_block)
                    added = True

                if added:
                    self.blocks_mined += 1
                    print(f"⛏️ MINED #{new_block.index} {h} -> 50 BEL to {self.wallet_str[:12]}...")
                    return new_block
                else:
                    # Si falla por chain, reinicia
                    return None
            nonce += 1
            if nonce % 5000 == 0:
                time.sleep(0.001) # no quemar CPU
        return None

    def start(self):
        if self.running:
            return
        self.running = True
        def loop():
            while self.running:
                self._mine_one()
                time.sleep(0.2)
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()
        print(f"⛏️ Miner started for {self.wallet_str[:16]}... diff={self.difficulty}")

    def stop(self):
        self.running = False
        print("Miner stopped")

    # Compatibilidad con api.py que llama start_mining / stop_mining
    def start_mining(self): return self.start()
    def stop_mining(self): return self.stop()

    def get_mining_stats(self):
        return {
            "running": self.running,
            "blocks_mined": self.blocks_mined,
            "hashes": self.hashes,
            "difficulty": self.difficulty,
            "wallet": self.wallet_str
        }
