
import hashlib, os
class Wallet:
    def __init__(self):
        self.private_key=os.urandom(32).hex()
        self.public_key=hashlib.sha256(self.private_key.encode()).hexdigest()[:34]
        self.address="BEL1Q"+self.public_key[:30].upper()
    def get_address(self):
        return self.address
