#!/bin/sh
set -e
if ! which truffle; then
    echo 'truffle not found'
    exit 1
fi

if [ ! -r './truffle.js' ]; then
    truffle init
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

cp ./Paket.sol ./contracts/.
cat << EOF
migrate --reset
Paket.deployed().then(function(i){p = i;})
EOF
truffle develop
