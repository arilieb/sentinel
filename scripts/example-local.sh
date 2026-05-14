#!/bin/bash

set -e
# To run this script you need to run the following command in a separate terminals:
#   > kli witness demo
# and from the vLEI repo run:
#   > vLEI-server -s ./schema/acdc -c ./samples/acdc/ -o ./samples/oobis/
#
kli init --name External --salt 0ACDEyMzQ1Njc4OWxtbm9ext --nopasscode --config-dir ${SENTINEL_SCRIPT_DIR} --config-file sentinel-config
kli incept --name External --alias External --file ${SENTINEL_SCRIPT_DIR}/data/base-aid.json

kli init --name External-sentinel --salt 0ACDEyMzQ1Njc4OWxtbmsent --nopasscode --config-dir ${SENTINEL_SCRIPT_DIR} --config-file sentinel-config
kli incept --name External-sentinel --alias External-sentinel --file ${SENTINEL_SCRIPT_DIR}/data/incept-no-witnesses.json

kli init --name QVI --salt 0ACDEyMzQ1Njc4OWxtbm9qvi --nopasscode --config-dir ${SENTINEL_SCRIPT_DIR} --config-file sentinel-config
kli incept --name QVI --alias QVI --file ${SENTINEL_SCRIPT_DIR}/data/base-aid.json

