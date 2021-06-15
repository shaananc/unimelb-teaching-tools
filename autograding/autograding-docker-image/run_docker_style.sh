#!/bin/bash
if [ "$#" -ne 1 ]; then
    echo "usage: run_docker_check.sh submission_dir"
fi

function abspath {
    if [[ -d "$1" ]]; then
        pushd "$1" >/dev/null
        pwd
        popd >/dev/null
    elif [[ -e "$1" ]]; then
        pushd "$(dirname "$1")" >/dev/null
        echo "$(pwd)/$(basename "$1")"
        popd >/dev/null
    else
        echo "$1" does not exist! >&2
        return 127
    fi
}

PATH_TO_STUDENT_CODE=$(abspath $1)
docker run --volume=$PATH_TO_STUDENT_CODE:/src --rm -ti shaananc/check50 style50 /src/program.c
