#!/bin/sh
set -e

if ! lsof -Pi :8545 -sTCP:LISTEN -t; then
    echo 'no RPC found on localhost'
    exit 1
fi

if ! which truffle; then
    echo 'truffle not found'
    exit 1
fi

# Initialize truffle if needed.
if [ ! -r './truffle.js' ]; then
    truffle init
    ln ./Paket.sol ./contracts/.
    npm install zeppelin-solidity

    cat << EOF > ./truffle.js
module.exports = {
  // See <http://truffleframework.com/docs/advanced/configuration>
  // to customize your Truffle configuration!
  networks: {
    development: {
      host: "localhost",
      port: 8545,
      network_id: "*" // Match any network id
    }
  }
};
EOF

    cat << EOF > ./migrations/2_deploy_contracts.js
const Paket = artifacts.require("./Paket");
module.exports = function(deployer, network, accounts){
    deployer.deploy(Paket);
};
EOF

fi

# Initialize swagger if needed.
[ -d swagger-ui ] || git clone --depth 1 https://github.com/swagger-api/swagger-ui

# Deploy contract and set address.
PAKET_ADDRESS="$(truffle migrate --reset | grep -Po '(?<=Paket: ).*')"

# Get ABI.
PAKET_ABI="$(solc --abi Paket.sol | sed -e '/Paket.sol:Paket/,/=======/{//!b};d' | tail -n+2)"


# Run flask
export PAKET_ADDRESS
export PAKET_ABI

export FLASK_APP=paket.py
export FLASK_DEBUG=1
python -m flask run
