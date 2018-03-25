import hashlib
import json
import requests

from time import time
from urllib.parse import urlparse
from textwrap import dedent
from uuid import uuid4

from flask import Flask, jsonify, request

class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()
        # genesis block
        self.new_block(previous_hash=1, proof=1000)

    def register_node(self,address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid
        :param chain: <list> A blockchain
        :return: <bool> True if valid, False if not
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False
            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        This is our Consensus Algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        :return: <bool> True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # if there's a node in neighbours whose chain is longer than ours, replace ours
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True
        return False


    def new_block(self,proof, previous_hash=None):
        #place new block
        #block: index, timestamp, list of transactions, proof, hash of the previous block
        #
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }
        #once a block is finished, the transaction is finished
        #record transaction, and clear your shoping cart :)
        self.chain.append(block)
        self.current_transactions = []

        return block
        pass

    def new_transaction(self,sender, recipient, amount):
        # add new transaction
        self.current_transactions.append({

            'sender': sender,
            'recipient': recipient,
            'amount': amount,

        })

        # return the index of the potential block, waiting to be mined
        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        # hash a block

        #create hash for block

        block_string = json.dumps(block,sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()


        pass

    @property
    def last_block(self):
        #return last block
        return self.chain[-1]


        pass


    #Proof of work, just to find a number solves a problem. The number should be difficult to find but easy to verify
    #Bitcoin use Hashcash

    
    def proof_of_work(self, last_proof):
        '''
        Proof of work algorithm:
            - find a number p' that hash(p,p') satisfy some rules, p is last proof
        :param last_proof: 
        :return: proof
        '''
        proof = 0
        while not self.valid_proof(last_proof,proof):
            proof += 1

        return proof

    def valid_proof(self,proof1,proof2):
        # consider if the first three digits of hash result to be 001
        guess = f'{proof1}{proof2}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:3] == '001'

#instantiate Node
app = Flask(__name__)

#Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-','')

#Create blockchain
blockchain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # reward the miner, create a new transaction for miner, from sender 0
    blockchain.new_transaction(
        sender='0',
        recipient=node_identifier,
        amount=1,
    )

    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': 'New Block Forged',
        'index': block['index'],
        'transactions': block['transactions'],
        'proof':block['proof'],
        'previous_hash': block['previous_hash']
    }



    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    #if all good, go create a new transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response),201

@app.route('/chain', methods=['POST'])
def full_chain():
    response = {
        'chain' : blockchain.chain,
        'length' : len(blockchain.chain)
    }
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200






if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)


























