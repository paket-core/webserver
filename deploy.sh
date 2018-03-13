#!/bin/bash
set -o allexport
. paket.env
set +o allexport

if ! lsof -Pi :8545 -sTCP:LISTEN -t; then
    node ./node_modules/ganache-cli/build/cli.node.js &
fi

if ! which truffle; then
    echo 'truffle not found'
    exit 1
fi

if ! which solc; then
    echo 'solc not found'
    exit 1
fi

missing_packages="$(comm -23 <(sort requirements.txt) <(pip freeze | grep -v '0.0.0' | sort))"
if [ "$missing_packages" ]; then
    echo "The following packages are missing: $missing_packages"
    exit 1
fi

# Initialize truffle and zeppelin if needed.
if [ ! -r 'truffle.js' ]; then
    # Ugly hack because truffle will only init in an empty directory.
    mkdir truffle
    cd truffle
    truffle init
    cd ..
    mv truffle/* .
    rmdir truffle

    ln ./Paket.sol ./contracts/.
    cat << EOF > truffle.js
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
    npm install zeppelin-solidity
fi

# Deploy contract and set address.
PAKET_ADDRESS="$(truffle migrate --reset | grep -Po '(?<=Paket: ).*')"
export PAKET_ADDRESS

# Get ABI.
PAKET_ABI="$(solc --abi Paket.sol | sed -e '/Paket.sol:Paket/,/=======/{//!b};d' | tail -n+2)"
export PAKET_ABI

flask run --host=0.0.0.0
