#!/bin/bash
# Deploy a PaKeT server.

# Parse options
usage() { echo 'Usage: ./deploy.sh [a|create-all] [l|create-stellar] [f|fund-stellar] [d|create-db] [t|test] [s|shell] [r|run-server]'; }
if ! [ "$1" ]; then
    if [ "$BASH_SOURCE" == "$0" ]; then
        usage
        return 0 2>/dev/null
        exit 0
    fi
fi
while [ "$1" ]; do
    case "$1" in
        a|all)
            create_stellar=1
            fund_stellar=1
            create_db=1
            _test=1
            shell=1
            run=1;;
        l|create-stellar)
            create_stellar=1;;
        f|fund-stellar)
            fund_stellar=1;;
        d|create-db)
            create_db=1;;
        t|test)
            _test=1;;
        s|shell)
            shell=1;;
        r|run-server)
            run=1;;
        *)
            usage
            return 0 2>/dev/null
            exit 0;;
    esac
    shift
done

# Export environment variables.
set -o allexport
. paket.env
set +o allexport

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

# Make sure horizon server is reachable.
if ! curl "$PAKET_HORIZON_SERVER"; then
    echo "Can't connect to horizon server $PAKET_HORIZON_SERVER"
    return 1 2>/dev/null
    exit 1
fi

[ "$create_db" ] && export PAKET_CREATE_DB=1 && rm paket.db
[ "$create_stellar" ] && export PAKET_CREATE_STELLAR=1
[ "$fund_stellar" ] && export PAKET_FUND_STELLAR=1
python -c "import api.server; api.server.init_sandbox()"

[ "$_test" ] && python -m unittest api.test

[ "$shell" ] && python -ic 'import logger; logger.setup(); import db; import paket; p = paket'

[ "$run" ] && FLASK_APP=api/server.py flask run --host=0.0.0.0

return 0 2>/dev/null
exit 0
