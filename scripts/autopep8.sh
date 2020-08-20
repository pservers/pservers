#!/bin/bash

FILES="./pservers"
LIBFILES=""
LIBFILES="${LIBFILES} $(find ./lib -name '*.py' | tr '\n' ' ')"

autopep8 -ia --ignore=E501,E402 ${FILES} ${LIBFILES}