#!/usr/bin/env python3
'Test Paket interface.'
import json
import web3
# pylint: disable=no-member
# Pylint has a hard time with dynamic members of web3.

def get_contract():
    'Get our contract.'
    w_3 = web3.Web3(web3.HTTPProvider('http://localhost:8545'))

    with open('paket.address', 'r') as address_file:
        address = address_file.read()[:-1]

    with open('paket.abi', 'r') as abi_file:
        abi = json.loads(abi_file.read()[:-1])

    return w_3.eth.contract(address=address, abi=abi)

if __name__ == '__main__':
    c = get_contract()
    o = c.call().owner()
    b = c.call().balanceOf(o)
    print(o, b)
