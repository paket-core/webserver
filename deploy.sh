#!/bin/bash
# Deploy a PaKeT server.

# Requires python3 and python packages (as specified in requirements.txt).
if ! which python3; then
    echo 'python3 not found'
    return 1 2>/dev/null
    exit 1
fi

missing_packages="$(comm -23 <(sort requirements.txt) <(pip freeze | grep -v '0.0.0' | sort))"
if [ "$missing_packages" ]; then
    echo "The following packages are missing: $missing_packages"
    return 1 2>/dev/null
    exit 1
fi

# Export environment variables.
set -o allexport
. paket.env
set +o allexport

# Make sure horizon server is reachable.
if ! curl "$PAKET_HORIZON_SERVER"; then
    echo "Can't connect to horizon server $PAKET_HORIZON_SERVER"
    return 1 2>/dev/null
    exit 1
fi

# Remove existing database and initialize a new one.
rm paket.db
python -c 'import api; api.init_sandbox()'

# Run server if script is run directly (and not sourced).
ret=$?
[ "$BASH_SOURCE" == "$0" ] && flask run --host=0.0.0.0 || return $ret
