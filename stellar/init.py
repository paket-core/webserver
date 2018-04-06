#!/usr/bin/env python3
# pylint: disable=missing-docstring,import-error
import requests
import stellar_base.address
import stellar_base.asset
import stellar_base.builder
import stellar_base.keypair

PERSIST = True
HORIZON = 'https://horizon-testnet.stellar.org' #'https://34.245.103.20'


def get_keypair(seed=None):
    keypair = stellar_base.keypair.Keypair.from_seed(
        seed if seed else stellar_base.keypair.Keypair.random().seed())
    keypair.__class__ = type('DisplayKeypair', (stellar_base.keypair.Keypair,), {
        '__repr__': lambda self: "KeyPair ({})".format(self.address().decode())})
    return keypair
str(get_keypair())


def get_details(address):
    # Allow keypairs as args.
    if isinstance(address, stellar_base.keypair.Keypair):
        address = address.address().decode()
    details = stellar_base.address.Address(address, horizon=HORIZON)
    try:
        details.get()
    # Create and fund non existing accounts.
    except stellar_base.utils.AccountNotExistError:
        print("creating and funding account {}".format(address))
        request = requests.get("https://friendbot.stellar.org/?addr={}".format(address))
        if request.status_code != 200:
            raise Exception("Funding request failed - {}".format(request.content))
        details.get()
    return details


if PERSIST:
    [ISSUER, LAUNCHER, COURIER, RECIPIENT] = [get_keypair(seed) for seed in [
        'SC2PO5YMP7VISFX75OH2DWETTEZ4HVZOECMDXOZIP3NBU3OFISSQXAEP',
        'SDJGBJZMQ7Z4W3KMSMO2HYEV56DJPOZ7XRR7LJ5X2KW6VKBSLELR7MRQ',
        'SBOLPN4HNTCLA3BMRS6QG62PXZUFOZ5RRMT6LPJHUPGQLBP5PZY4YFIT',
        'SA5OXLJ2JCX4PF3G5WKSG66CXJQXQFCT62NQJ747XET5E2FR6TVIE4ET']]
else:
    [ISSUER, LAUNCHER, COURIER, RECIPIENT] = [get_keypair() for seed in range(4)]
PARTICIPANTS = [LAUNCHER, COURIER, RECIPIENT]


def trust(account):
    print("adding trust to {}".format(account.address().decode()))
    builder = stellar_base.builder.Builder(horizon=HORIZON, secret=account.seed())
    builder.append_trust_op(ISSUER.address().decode(), 'BUL')
    builder.sign()
    return builder.submit()


def get_bul_balance(account):
    'Get acount BUL balance. Trust if needed.'
    balances = get_details(account).balances
    for balance in balances:
        if balance.get('asset_code') == 'BUL' and balance.get('asset_issuer') == ISSUER.address().decode():
            return float(balance['balance'])
    # If we are here, the account is not trusted. Fix it if possible and call again.
    # This will continue ad infinitum if the backend is faulty :)
    if account == ISSUER:
        return None
    else:
        trust(account)
    return get_bul_balance(account)


def pay(source, target, amount):
    print("sending {} BUL from {} to {}".format(amount, source.address().decode(), target.address().decode()))
    builder = stellar_base.builder.Builder(horizon=HORIZON, secret=source.seed())
    builder.append_payment_op(target.address().decode(), amount, 'BUL', ISSUER.address().decode())
    builder.sign()
    return builder.submit()


def fund_buls(account):
    try:
        balance = get_bul_balance(account)
        assert balance >= 100
    except AssertionError:
        print("{} has only {} BUL".format(account.address(), balance))
        pay(ISSUER, account, 1000 - balance)
        balance = get_bul_balance(account)
    return account.address().decode()[:5], balance


def launch(launcher, courier, recipient, payment, collateral):
    escrow = get_keypair()

    builder = stellar_base.builder.Builder(horizon=HORIZON, secret=courier.seed())
    builder.append_create_account_op(destination=escrow.address().decode(), starting_balance=5)
    builder.sign()
    builder.submit()
    trust(escrow)

    builder = stellar_base.builder.Builder(horizon=HORIZON, secret=escrow.seed())
    builder.append_set_options_op(
        signer_address=courier.address().decode(),
        signer_type='ed25519PublicKey',
        signer_weight=2)
    builder.append_set_options_op(
        signer_address=launcher.address().decode(),
        signer_type='ed25519PublicKey',
        signer_weight=1)
    builder.append_set_options_op(
        signer_address=recipient.address().decode(),
        signer_type='ed25519PublicKey',
        signer_weight=1)
    builder.append_set_options_op(
        master_weight=0, low_threshold=1, med_threshold=3, high_threshold=4)
    builder.sign()
    builder.submit()

    sequence = int(get_details(courier).sequence) + 1
    builder = stellar_base.builder.Builder(horizon=HORIZON, secret=courier.seed(), sequence=sequence)
    builder.append_payment_op(
        launcher.address().decode(), payment + collateral,
        'BUL', ISSUER.address().decode(),
        escrow.address().decode())
    builder.sign()
    refund_tx = builder.gen_xdr()

    pay(launcher, escrow, payment)
    pay(courier, escrow, collateral)

    return escrow.address().decode(), refund_tx


def test():
    escrow_address, ptx = launch(LAUNCHER, COURIER, RECIPIENT, 10, 50)
    print(get_details(escrow_address).balances)
    print(get_details(escrow_address).signers)
    print(get_details(escrow_address).thresholds)
    print([(account.address().decode()[:5], get_bul_balance(account)) for account in PARTICIPANTS])
    builder = stellar_base.builder.Builder(horizon=HORIZON, secret=LAUNCHER.seed())
    builder.import_from_xdr(ptx)
    builder.sign()
    print(builder.submit())
    print([(account.address().decode()[:5], get_bul_balance(account)) for account in PARTICIPANTS])


if __name__ == '__main__':
    print([fund_buls(account) for account in PARTICIPANTS])
    test()
