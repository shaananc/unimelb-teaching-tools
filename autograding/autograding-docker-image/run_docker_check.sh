#!/bin/bash
if [ "$#" -ne 1 ]; then
    echo "usage: run_docker_check.sh submission_dir dist_files_dir check50_checks_dir"
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
PATH_TO_DISTRIBUTED_CODE=$(abspath $2)
PATH_TO_CS50_CHECKS=$(abspath $3)
docker run --volume=$PATH_TO_CS50_CHECKS:/opt/check_files --volume=$PATH_TO_STUDENT_CODE:/src --volume=$PATH_TO_DISTRIBUTED_CODE:/dist --rm -ti shaananc/check50 check50 -o json --dev /opt/check_files
