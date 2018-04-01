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


def get_details(pubkey):
    address = stellar_base.address.Address(pubkey)
    address.get()
    return address


def trust(account):
    builder = stellar_base.builder.Builder(secret=account.seed())
    builder.append_trust_op(ISSUER.address().decode(), 'BUL')
    builder.sign()
    builder.submit()


def get_bul_balance(account):
    'Get acount BUL balance. Create, fund and trust if needed.'
    pubkey = account.address().decode()
    try:
        balances = get_details(pubkey).balances
        for balance in balances:
            if balance.get('asset_code') == 'BUL' and balance.get('asset_issuer') == ISSUER.address().decode():
                return float(balance['balance'])

    # Create and fund non existing accounts.
    except stellar_base.utils.AccountNotExistError:
        request = requests.get("https://friendbot.stellar.org/?addr={}".format(pubkey))
        if request.status_code != 200:
            raise Exception("Funding request failed - {}".format(request.content))

    # If we are here, the account is not trusted. Fix it if possible and call again.
    if pubkey == ISSUER.address().decode():
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
        pay(ISSUER, account, 100 - balance)
        balance = get_bul_balance(account)
    return (account.seed()[:5], balance)


def fund_participants():
    for account in PARTICIPANTS:
        print(fund_buls(account))


fund_participants()


def print_balances():
    for account in PARTICIPANTS:
        print(account.seed()[:5], get_bul_balance(account))


print_balances()


def launch(launcher, courier, recipient, payment, collateral):
    escrow = get_keypair(random_seed())
    builder = stellar_base.builder.Builder(secret=courier.seed())
    builder.append_create_account_op(escrow.address().decode(), 1)
    builder.submit()
    get_bul_balance(escrow)
    builder = stellar_base.builder.Builder(secret=courier.seed())
    builder.append_set_options_op(
        master_weight=2, low_threshold=2, med_threshold=2, high_threshold=4)
    builder.append_set_options_op(signer_address=recipient.address().decode())
    builder.append_set_options_op(signer_address=launcher.address().decode())
    builder.sign()
    builder.submit()
    pay(launcher, escrow, payment)
    pay(courier, escrow, collateral)
    return get_bul_balance(escrow)


print(launch(LAUNCHER, COURIER, RECIPIENT, 10, 50))
print_balances()
