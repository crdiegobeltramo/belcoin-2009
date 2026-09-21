
import hashlib, time, json
class Block:
    def __init__(self, index, timestamp, transactions, previous_hash, nonce=0):
        self.index=index
        self.timestamp=timestamp
        self.transactions=transactions
        self.previous_hash=previous_hash
        self.nonce=nonce
        self.hash=self.calculate_hash()
    def calculate_hash(self):
        s=f"{self.index}{self.timestamp}{json.dumps(self.transactions, default=str)}{self.previous_hash}{self.nonce}"
        return hashlib.sha256(s.encode()).hexdigest()
    def to_dict(self):
        return {"index":self.index,"timestamp":self.timestamp,"transactions":self.transactions,"previous_hash":self.previous_hash,"nonce":self.nonce,"hash":self.hash}
