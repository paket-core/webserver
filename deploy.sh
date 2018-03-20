#!/bin/bash
# Deploy a PaKeT server.

# Requires python3 (see python requirements in requirements.txt), npm, truffle,
# solc, and a running ethereum RPC server (we are using ganache-cli).

missing_packages="$(comm -23 <(sort requirements.txt) <(pip freeze | grep -v '0.0.0' | sort))"
if [ "$missing_packages" ]; then
    echo "The following packages are missing: $missing_packages"
    return 1
    exit 1
fi

if ! which npm; then
    echo 'npm not found'
    return 1
    exit 1
fi

if ! which truffle; then
    echo 'truffle not found'
    return 1
    exit 1
fi

if ! which solc; then
    echo 'solc not found'
    return 1
    exit 1
fi

if ! lsof -Pi :8545 -sTCP:LISTEN -t; then
    echo 'no running rpc server found on standard port'
    return 1
    exit 1
fi

# Install zeppelin if needed.
if [ ! -e './node_modules/zeppelin-solidity/' ]; then
    npm install zeppelin-solidity
fi

# Initialize truffle if needed.
if [ ! -e 'truffle.js' ]; then
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
fi

# Export environment variables.
set -o allexport
. paket.env
set +o allexport

# Deploy contract and get address.
PAKET_ADDRESS="$(truffle migrate --reset | grep -Po '(?<=Paket: ).*')"
export PAKET_ADDRESS

# Get ABI.
PAKET_ABI="$(solc --abi Paket.sol | sed -e '/Paket.sol:Paket/,/=======/{//!b};d' | tail -n+2)"
export PAKET_ABI

# Remove existing database and initialize a new one.
rm paket.db
python -c 'import api; api.init_sandbox()'

# Run server if script is run directly (and not sourced).
[ "$BASH_SOURCE" == "$0" ] && flask run --host=0.0.0.0
