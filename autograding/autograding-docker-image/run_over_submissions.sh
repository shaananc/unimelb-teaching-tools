#!/bin/bash
for d in /Users/shaananc/Downloads/unimelb-comp10002-2021-s1-assignment1/non-anonymised/*/; do
    echo $d
    ./run_docker_check.sh $d/unimelb-comp10002-2021-s1-assignment1/on-time/code | tee $d/results.json
    ./run_docker_style.sh $d/unimelb-comp10002-2021-s1-assignment1/on-time/code | tee $d/style.json
done
# ./run_docker_check.sh submissions/test
