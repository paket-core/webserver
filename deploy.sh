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

truffle migrate --reset | grep -Po '(?<=Paket: ).*' > paket.address
solc --abi Paket.sol | tail -1 > paket.abi
./paket.py
