
import hashlib, time
def mine_block(block, difficulty=4):
    prefix="0"*difficulty
    while not block.hash.startswith(prefix):
        block.nonce+=1
        block.hash=block.calculate_hash()
    return block
