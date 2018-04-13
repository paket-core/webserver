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

# Optionally remove existing database and initialize a new one.
if [ "$1" = persist ]; then
    shift
else
    rm paket.db
    if [ "$1" = db_only ]; then
        shift
        python -c 'import api.server; api.server.init_sandbox(False)'
    else
        python -c 'import api.server; api.server.init_sandbox(True)'
    fi
fi

# Run web server if script is run directly.
if [ "$BASH_SOURCE" == "$0" ]; then
    FLASK_APP=api/server.py flask run --host=0.0.0.0
# If it is sourced run python shell.
else
    if [ "$1" = shell ]; then
        python -ic 'import logger; logger.setup(); import db; import paket'
    fi
fi
