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

LOGGER = logging.getLogger('pkt.paket')

WEB3_SERVER = os.environ.get('PAKET_WEB3_SERVER', 'http://localhost:8545')
W3 = web3.Web3(web3.HTTPProvider(WEB3_SERVER))

ADDRESS = os.environ['PAKET_ADDRESS']
ABI = json.loads(os.environ['PAKET_ABI'])
PAKET = W3.eth.contract(address=ADDRESS, abi=ABI)

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
    return {
        'paket_id': str(paket_id),
        'creation_promise': PAKET.transact({'from': user}).create(paket_id, recipient, deadline),
        'payment_promise': PAKET.transact({'from': user}).commitPayment(paket_id, courier, payment)}


def get_paket_details(paket_id):
    'Get paket details.'
    (
        recipient, deadline, payment_benificieries, collateral_refundees, payment_refundees, collateral_benificieries
    ) = PAKET.call().get(paket_id)
    return {
        'recipient': recipient,
        'deadline': deadline,
        'payment_benificieries': payment_benificieries,
        'collateral_refundees': collateral_refundees,
        'payment_refundees': payment_refundees,
        'collateral_benificieries': collateral_benificieries}


def confirm_delivery(user, paket_id):
    'Confirm a delivery.'
    return PAKET.transact({'from': user}).payout(paket_id)


def commit_collateral(user, paket_id, collateral_benificiery, collateral_buls):
    'Commit collateral on a paket.'
    LOGGER.warning("%s %s", paket_id, type(paket_id))
    LOGGER.warning("%s %s", collateral_benificiery, type(collateral_benificiery))
    LOGGER.warning("%s %s", collateral_buls, type(collateral_buls))
    return PAKET.transact({'from': user}).commitCollateral(paket_id, collateral_benificiery, collateral_buls)


def accept_paket(user, paket_id, collateral_benificiery, collateral_buls):
    """
    Accept a paket.
    If user is the recipient, confirm the delivery.
    If user is a courier, commit required collateral to collateral_benificiery.
    """
    LOGGER.warning(paket_id)
    LOGGER.warning(get_paket_details(paket_id))
    if user == get_paket_details(paket_id)['recipient']:
        return confirm_delivery(user, paket_id)
    return commit_collateral(user, paket_id, collateral_benificiery, collateral_buls)


# pylint: disable=missing-docstring
def get_paket_balance(user, paket_id):
    return PAKET.call({'from': user}).paketSelfInterest(paket_id)


def cover_collateral(user, paket_id, courier, collateral):
    return PAKET.transact({'from': user}).coverCollateral(paket_id, courier, collateral)


def relay_payment(user, paket_id, courier, payment):
    return PAKET.transact({'from': user}).relayPayment(paket_id, courier, payment)


def refund(user, paket_id):
    return PAKET.transact({'from': user}).refund(paket_id)


# This is an ugly, temporary usage of ganache's internal keys.
OWNER, LAUNCHER, RECIPIENT, COURIER = W3.eth.accounts[:4]


def test():
    addresses = OWNER, LAUNCHER, RECIPIENT, COURIER

    def show_balances():
        print("""
        owner - {}
        launcher - {}
        recipient - {}
        courier - {}""".format(*[get_balance(address) for address in addresses]))

    show_balances()

    transfer_buls(OWNER, LAUNCHER, 1000)
    transfer_buls(OWNER, RECIPIENT, 1000)
    transfer_buls(OWNER, COURIER, 1000)
    show_balances()

    paket_id = launch_paket(LAUNCHER, RECIPIENT, int(time.time()) + 100, COURIER, 100)
    show_balances()

    confirm_delivery(RECIPIENT, paket_id)
    show_balances()


if __name__ == '__main__':
    test()
