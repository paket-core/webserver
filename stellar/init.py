#!/usr/bin/env python3
# pylint: disable=missing-docstring,import-error
import requests
import stellar_base.address
import stellar_base.asset
import stellar_base.builder
import stellar_base.keypair


PERSIST = True


def random_seed():
    return stellar_base.keypair.Keypair.random().seed()
random_seed()


def get_keypair(seed):
    return stellar_base.keypair.Keypair.from_seed(seed)


if PERSIST:
    [ISSUER, LAUNCHER, COURIER, RECIPIENT] = [get_keypair(seed) for seed in [
        'SC2PO5YMP7VISFX75OH2DWETTEZ4HVZOECMDXOZIP3NBU3OFISSQXAEP',
        'SDJGBJZMQ7Z4W3KMSMO2HYEV56DJPOZ7XRR7LJ5X2KW6VKBSLELR7MRQ',
        'SBOLPN4HNTCLA3BMRS6QG62PXZUFOZ5RRMT6LPJHUPGQLBP5PZY4YFIT',
        'SA5OXLJ2JCX4PF3G5WKSG66CXJQXQFCT62NQJ747XET5E2FR6TVIE4ET']]
else:
    ISSUER = get_keypair(random_seed())
    LAUNCHER = get_keypair(random_seed())
    COURIER = get_keypair(random_seed())
    RECIPIENT = get_keypair(random_seed())
PARTICIPANTS = [LAUNCHER, COURIER, RECIPIENT]


def get_details(account):
    try:
        address = stellar_base.address.Address(account.address().decode())
    except AttributeError:
        address = stellar_base.address.Address(account)
    address.get()
    return address


def trust(account):
    builder = stellar_base.builder.Builder(secret=account.seed())
    builder.append_trust_op(ISSUER.address().decode(), 'BUL')
    builder.sign()
    builder.submit()


def get_bul_balance(account):
    'Get acount BUL balance. Create, fund and trust if needed.'
    try:
        balances = get_details(account).balances
        for balance in balances:
            if balance.get('asset_code') == 'BUL' and balance.get('asset_issuer') == ISSUER.address().decode():
                return float(balance['balance'])

    # Create and fund non existing accounts.
    except stellar_base.utils.AccountNotExistError:
        request = requests.get("https://friendbot.stellar.org/?addr={}".format(account.address().decode()))
        if request.status_code != 200:
            raise Exception("Funding request failed - {}".format(request.content))

    # If we are here, the account is not trusted. Fix it if possible and call again.
    if account == ISSUER:
        return None
    else:
        trust(account)
    return get_bul_balance(account)


assert get_bul_balance(ISSUER) is None


def pay(source, target, amount):
    builder = stellar_base.builder.Builder(secret=source.seed())
    builder.append_payment_op(target.address().decode(), amount, 'BUL', ISSUER.address().decode())
    builder.sign()
    return builder.submit()


def fund_buls(account):
    try:
        balance = get_bul_balance(account)
        assert balance >= 100
    except AssertionError:
        pay(ISSUER, account, 1000 - balance)
        balance = get_bul_balance(account)
    return (account.seed()[:5], balance)


def fund_participants():
    for account in PARTICIPANTS:
        print(fund_buls(account))


def print_balances():
    for account in PARTICIPANTS:
        print(account.seed()[:5], get_bul_balance(account))


def launch(launcher, courier, recipient, payment, collateral):
    escrow = get_keypair(random_seed())

    builder = stellar_base.builder.Builder(secret=courier.seed())
    builder.append_create_account_op(destination=escrow.address().decode(), starting_balance=5)
    builder.sign()
    builder.submit()
    trust(escrow)

    builder = stellar_base.builder.Builder(secret=escrow.seed())
    builder.append_set_options_op(
        source=escrow.address().decode(),
        signer_address=courier.address().decode(),
        signer_type='ed25519PublicKey',
        signer_weight=2)
    builder.append_set_options_op(
        source=escrow.address().decode(),
        signer_address=launcher.address().decode(),
        signer_type='ed25519PublicKey',
        signer_weight=1)
    builder.append_set_options_op(
        source=escrow.address().decode(),
        signer_address=recipient.address().decode(),
        signer_type='ed25519PublicKey',
        signer_weight=1)
    builder.append_set_options_op(
        master_weight=0, low_threshold=1, med_threshold=1, high_threshold=3)
    builder.sign()
    builder.submit()

    sequence = int(get_details(courier).sequence) + 1
    builder = stellar_base.builder.Builder(secret=courier.seed(), sequence=sequence)
    builder.append_payment_op(
        courier.address().decode(), payment + collateral,
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
    builder = stellar_base.builder.Builder(secret=RECIPIENT.seed())
    builder.import_from_xdr(ptx)
    builder.sign()
    builder = stellar_base.builder.Builder(secret=LAUNCHER.seed())
    builder.import_from_xdr(ptx)
    #builder.sign()
    print(builder.submit())


if __name__ == '__main__':
    #fund_participants()
    print_balances()
    test()
    print_balances()
