#!/usr/bin/env python3
import requests
import stellar_base.address
import stellar_base.asset
import stellar_base.builder
import stellar_base.keypair


def random_seed():
    return stellar_base.keypair.Keypair.random().seed()
random_seed()


def get_keypair(seed):
    return stellar_base.keypair.Keypair.from_seed(seed)


def get_details(pubkey):
    address = stellar_base.address.Address(pubkey)
    address.get()
    return address


def trust(account, asset_code, issuer):
    builder = stellar_base.builder.Builder(secret=account.seed())
    builder.append_trust_op(issuer, asset_code, None, account.address().decode())
    builder.sign()
    return builder.submit()
    return get_details(account.address().decode()).balances


def fund_and_trust(account, asset_code, issuer):
    pubkey = account.address().decode()
    try:
        balances = get_details(pubkey).balances
        if pubkey == issuer:
            return balances
        for balance in balances:
            if balance.get('asset_code') == 'BUL' and balance.get('asset_issuer') == issuer:
                return balance
    except stellar_base.utils.AccountNotExistError:
        request = requests.get("https://friendbot.stellar.org/?addr={}".format(pubkey))
        if request.status_code != 200:
            raise Exception("Funding request failed - {}".format(request.content))
    return trust(account, asset_code, issuer)


def pay(source, target, asset_code, issuer, amount):
    builder = stellar_base.builder.Builder(secret=source.seed())
    builder.append_payment_op(target, amount, asset_code, issuer)
    builder.sign()
    return builder.submit()


ISSUER = get_keypair(random_seed())
DISTRIBUTOR = get_keypair(random_seed())
ISH = get_keypair(random_seed())
print([fund_and_trust(account, 'BUL', ISSUER.address().decode()) for account in [ISSUER, DISTRIBUTOR, ISH]])
print(pay(ISSUER, DISTRIBUTOR.address().decode(), 'BUL', ISSUER.address().decode(), 10))
print([get_details(account.address().decode()).balances for account in [ISSUER, DISTRIBUTOR, ISH]])
print(pay(DISTRIBUTOR, ISH.address().decode(), 'BUL', ISSUER.address().decode(), 1))
print([get_details(account.address().decode()).balances for account in [ISSUER, DISTRIBUTOR, ISH]])
