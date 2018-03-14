#!/usr/bin/env python3
"""Use PaKeT smart contract."""
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
db.init_db()
db.set_users({'owner': OWNER, 'launcher': LAUNCHER, 'recipient': RECIPIENT, 'courier': COURIER})


def set_account(address):
    """Set the default account."""
    W3.eth.defaultAccount = address


def get_balance(address):
    """Get balance for an address."""
    return PAKET.call().balanceOf(address)


def transfer_buls(user, to_address, amount):
    """Transfer BULs."""
    return PAKET.transact({'from': user}).transfer(to_address, amount)


def launch_paket(user, recipient, deadline, courier, payment):
    """Launch a paket."""
    # We are using only 128 bits here, out of the available 256.
    paket_id = uuid.uuid4().int
    LOGGER.error("%s %s %s", paket_id, recipient, deadline)
    LOGGER.error("%s %s %s", type(paket_id), type(recipient), type(deadline))
    return {
        'paket_id': paket_id,
        'creation_promise': PAKET.transact({'from': user}).create(paket_id, recipient, deadline),
        'payment_promise': PAKET.transact({'from': user}).commitPayment(paket_id, courier, payment)}


# pylint: disable=missing-docstring
def get_paket_balance(user, paket_id):
    return PAKET.call({'from': user}).paketSelfInterest(paket_id)


def commit_collateral(user, paket_id, launcher, collateral):
    return PAKET.transact({'from': user}).commitCollateral(paket_id, launcher, collateral)


def cover_collateral(user, paket_id, courier, collateral):
    return PAKET.transact({'from': user}).coverCollateral(paket_id, courier, collateral)


def relay_payment(user, paket_id, courier, payment):
    return PAKET.transact({'from': user}).relayPayment(paket_id, courier, payment)


def refund(user, paket_id):
    return PAKET.transact({'from': user}).refund(paket_id)


def confirm_delivery(user, paket_id):
    return PAKET.transact({'from': user}).payout(paket_id)


def accept_paket(user, paket_id):
    paket = PAKET.call().get(paket_id)
    return paket


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

    transfer_buls(owner, launcher, 1000)
    transfer_buls(owner, recipient, 1000)
    transfer_buls(owner, courier, 1000)
    show_balances()

    paket_id = launch_paket(launcher, recipient, int(time.time()) + 100, courier, 100)
    show_balances()

    confirm_delivery(recipient, paket_id)
    show_balances()


if __name__ == '__main__':
    test()
