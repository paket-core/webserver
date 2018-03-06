#!/usr/bin/env python3
'Use PaKeT smart contract.'
import json
import os
import time
import uuid

import web3
# pylint: disable=no-member
# Pylint has a hard time with dynamic members.

WEB3_SERVER = os.environ.get('PAKET_WEB3_SERVER', 'http://localhost:8545')
W3 = web3.Web3(web3.HTTPProvider(WEB3_SERVER))

ADDRESS = os.environ['PAKET_ADDRESS']
ABI = json.loads(os.environ['PAKET_ABI'])
PAKET = W3.eth.contract(address=ADDRESS, abi=ABI)

# pylint: disable=missing-docstring
def set_account(address):
    W3.eth.defaultAccount = address

def get_balance(address):
    return PAKET.call().balanceOf(address)

def transfer(address, amount):
    PAKET.transact().transfer(address, amount)

def get_paket_balance(paket_id):
    return PAKET.call().paketSelfInterest(paket_id)

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
    PAKET.transact().relayPayment(paket_id, courier, payment)

def refund(paket_id):
    PAKET.transact().refund(paket_id)

def confirm_delivery(paket_id):
    PAKET.transact().payout(paket_id)

def test():
    # This is an ugly, temporary usage of ganache's internal keys.
    addresses = owner, launcher, recipient, courier = W3.eth.accounts[:4]

    def show_balances():
        print("""
        owner - {}
        launcher - {}
        recipient - {}
        courier - {}""".format(*[get_balance(address) for address in addresses]))

    show_balances()

    set_account(owner)
    transfer(launcher, 1000)
    transfer(recipient, 1000)
    transfer(courier, 1000)
    show_balances()

    paket_idx = launch(recipient, int(time.time()) + 100, courier, 100)
    show_balances()

    set_account(recipient)
    confirm_delivery(paket_idx)
    show_balances()

if __name__ == '__main__':
    test()
