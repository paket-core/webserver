"""Use PaKeT smart contract."""
import logging
import os
import requests

import stellar_base.address
import stellar_base.asset
import stellar_base.builder
import stellar_base.keypair

import db

LOGGER = logging.getLogger('pkt.paket')


def get_keypair(seed=None):
    """Get a keypair from seed (default to random)."""
    keypair = stellar_base.keypair.Keypair.from_seed(
        seed if seed else stellar_base.keypair.Keypair.random().seed())
    keypair.__class__ = type('DisplayKeypair', (stellar_base.keypair.Keypair,), {
        '__repr__': lambda self: "KeyPair ({})".format(self.address().decode())})
    return keypair


def get_details(address):
    """Get address details."""
    details = stellar_base.address.Address(address)
    try:
        details.get()
    # Create and fund non existing accounts.
    except stellar_base.utils.AccountNotExistError:
        LOGGER.warning("creating and funding account %s", address)
        request = requests.get("https://friendbot.stellar.org/?addr={}".format(address))
        if request.status_code != 200:
            raise Exception("Funding request failed - {}".format(request.content))
        details.get()
    return details


ISSUER = get_keypair(os.environ['PAKET_USER_ISSUER'])


def trust(account):
    """Trust BUL from account."""
    LOGGER.debug("adding trust to %s", account.address().decode())
    builder = stellar_base.builder.Builder(secret=account.seed())
    builder.append_trust_op(ISSUER.address().decode(), 'BUL')
    builder.sign()
    return builder.submit()


def get_bul_balance(address):
    """Get acount BUL balance. Trust if needed."""
    balances = get_details(address).balances
    for balance in balances:
        if balance.get('asset_code') == 'BUL' and balance.get('asset_issuer') == ISSUER.address().decode():
            return float(balance['balance'])
    # If we are here, the account is not trusted. Fix it if possible and call again.
    # This will continue ad infinitum if the backend is faulty :)
    if address == ISSUER.address().decode():
        return None
    else:
        trust(get_keypair(db.get_user(address)['seed']))
    return get_bul_balance(address)


def send_buls(from_address, to_address, amount):
    """Transfer BULs."""
    LOGGER.into("sending %s BUL from %s to %s", amount, from_address, to_address)
    source = get_keypair(db.get_user(from_address)['seed'])
    builder = stellar_base.builder.Builder(secret=source.seed())
    builder.append_payment_op(to_address, amount, 'BUL', ISSUER.address().decode())
    builder.sign()
    return builder.submit()


class NotEnoughFunds(Exception):
    """Not enough funds for operations."""


def set_account(address):
    """Set the default account."""
    W3.eth.defaultAccount = address


def new_account():
    """Create a new account, fund it with ether, and unlock it."""
    new_address = W3.personal.newAccount('pass')
    W3.eth.sendTransaction({'from': W3.eth.accounts[0], 'to': new_address, 'value': 1000000000000})
    W3.personal.unlockAccount(new_address, 'pass')
    return new_address


def launch_paket(user, recipient, deadline, courier, payment):
    """Launch a paket."""
    # We are using only 128 bits here, out of the available 256.
    paket_id = uuid.uuid4().int
    try:
        return {
            'paket_id': str(paket_id),
            'creation_promise': PAKET.transact({'from': user}).create(paket_id, recipient, deadline),
            'payment_promise': PAKET.transact({'from': user}).commitPayment(paket_id, courier, payment)}
    except ValueError:
        raise NotEnoughFunds('Not Enough Funds. {} is needed'.format(payment))


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
    return PAKET.transact({'from': user}).commitCollateral(paket_id, collateral_benificiery, collateral_buls)


def accept_paket(user, paket_id, collateral_benificiery, collateral_buls):
    """
    Accept a paket.
    If user is the recipient, confirm the delivery.
    If user is a courier, commit required collateral to collateral_benificiery.
    """
    if user == get_paket_details(paket_id)['recipient']:
        return confirm_delivery(user, paket_id)
    return commit_collateral(user, paket_id, collateral_benificiery, collateral_buls)


# pylint: disable=missing-docstring
def get_paket_balance(user, paket_id):
    return PAKET.call({'from': user}).paketSelfInterest(paket_id)


def cover_collateral(user, paket_id, courier, collateral):
    return PAKET.transact({'from': user}).coverCollateral(paket_id, courier, collateral)


def relay_payment(user, paket_id, courier, payment):
    return PAKET.transact({'from': user}).relayPayment(int(paket_id), courier, payment)


def refund(user, paket_id):
    return PAKET.transact({'from': user}).refund(paket_id)
