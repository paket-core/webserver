#!/usr/bin/env python3
'Use PaKeT smart contract.'
import json
import logging
import os
import time
import uuid

import web3
# pylint: disable=no-member
# Pylint has a hard time with dynamic members.

import db

LOGGER = logging.getLogger('pkt.paket')

WEB3_SERVER = os.environ.get('PAKET_WEB3_SERVER', 'http://localhost:8545')
W3 = web3.Web3(web3.HTTPProvider(WEB3_SERVER))

ADDRESS = os.environ['PAKET_ADDRESS']
ABI = json.loads(os.environ['PAKET_ABI'])
PAKET = W3.eth.contract(address=ADDRESS, abi=ABI)

# This is an ugly, temporary usage of ganache's internal keys.
OWNER, LAUNCHER, RECIPIENT, COURIER = W3.eth.accounts[:4]
db.set_users({'owner': OWNER, 'launcher': LAUNCHER, 'recipient': RECIPIENT, 'courier': COURIER})


def get_user_address(user_id):
    'Get address of a user.'
    if W3.isAddress(user_id):
        return user_id
    address = db.get_address(user_id)
    if not W3.isAddress(address):
        LOGGER.error("user %s has invalid address %s", user_id, address)
        return None
    return address


def set_account(address):
    'Set the default account.'
    W3.eth.defaultAccount = address


def get_balance(address):
    'Get balance for an address.'
    return PAKET.call().balanceOf(address)


def transfer(user_address, to_address, amount):
    'Transfer BULs.'
    return PAKET.transact({'from': user_address}).transfer(to_address, amount)


# pylint: disable=missing-docstring
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

    transfer(owner, launcher, 1000)
    transfer(owner, recipient, 1000)
    transfer(owner, courier, 1000)
    show_balances()

    paket_idx = launch(recipient, int(time.time()) + 100, courier, 100)
    show_balances()

    set_account(recipient)
    confirm_delivery(paket_idx)
    show_balances()


if __name__ == '__main__':
    test()
