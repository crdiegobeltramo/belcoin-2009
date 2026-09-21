
import hashlib, json
class Transaction:
    def __init__(self, sender, recipient, amount, message=""):
        self.sender=sender
        self.recipient=recipient
        self.amount=amount
        self.message=message
    def to_dict(self):
        return {"sender":self.sender,"recipient":self.recipient,"amount":self.amount,"message":self.message}
