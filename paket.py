'API to PaKeT smart contract.'
import json
import os
import sys
import uuid

import web3
# pylint: disable=no-member
# Pylint has a hard time with dynamic members.

VERSION = '1'
RPC_SERVER = os.environ.get('PAKET_HOST', 'http://localhost:8545')
ADDRESS = os.environ['PAKET_ADDRESS']
ABI = json.loads(os.environ['PAKET_ABI'])

def get_w3(rpc_server=RPC_SERVER):
    'Get a provider.'
    return web3.Web3(web3.HTTPProvider(rpc_server))

W3 = get_w3()

def set_account(address):
    W3.eth.defaultAccount = address

def get_contract(address=ADDRESS, abi=ABI, w3=W3):
    'Get a contract.'
    return W3.eth.contract(address=address, abi=abi)

PAKET = get_contract()

def get_owner():
    return PAKET.call().owner()

def get_balance(address):
    return PAKET.call().balanceOf(address)

def transfer(address, amount):
    PAKET.transact().transfer(address, amount)

def get_paket_balance(paket_id):
    return PAKET.call().paketSelfInterest(paket_id);

def launch(recipient, deadline, courier, payment):
    # We are using only 128 bits here, out of the available 256.
    paket_id = uuid.uuid4().int
    PAKET.transact().create(paket_id, recipient, deadline)
    PAKET.transact().commitPayment(paket_id, courier, payment)
    return paket_id

def commit_collateral(paket_id, launcher, collateral):
    PAKET.transact().commitCollateral(paket_id, launcher, collateral)

def cover_collateral(paket_id, courier, collateral):
    PAKET.transact().coverCollateral(paket_id, courier, collateral)

def relay_payment(paket_id, courier, payment):
    PAKET.transact().relayPayment(paket_id, courier, collateral)

def refund(paket_id):
    PAKET.transact().refund(paket_id)

def confirm_delivery(paket_id):
    PAKET.transact().payout(paket_id)
