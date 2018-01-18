'API to PaKeT smart contract.'
import json
import os
import sys

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

def get_contract(address=ADDRESS, abi=ABI, w3=W3):
    'Get a contract.'
    return W3.eth.contract(address=address, abi=abi)

PAKET = get_contract()

def get_owner():
    return PAKET.call().owner()

def get_balance(address):
    return PAKET.call().balanceOf(address)

def get_paket_balance(paket_idx):
    return PAKET.call().paketSelfInterest(paket_idx);

def launch(recipient, deadline, courier, payment):
    paket_idx = PAKET.transact().create(recipient, deadline)
    PAKET.transact().commitPayment(paket_idx, courier, payment)
    return paket_idx

def commit_collateral(paket_idx, launcher, collateral):
    PAKET.transact().commitCollateral(paket_idx, launcher, collateral)

def cover_collateral(paket_idx, courier, collateral):
    PAKET.transact().coverCollateral(paket_idx, courier, collateral)

def relay_payment(paket_idx, courier, payment):
    PAKET.transact().relayPayment(paket_idx, courier, collateral)

def refund(paket_idx):
    PAKET.transact().refund(paket_idx)

def confirm_delivery(paket_idx):
    PAKET.transact().payout(paket_idx)
