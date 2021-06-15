for d in $(find $(pwd)/mash -d 1); do
    cd $d
    check50 --dev $(pwd)/mst-checker -o json --output-file ../../checker_output/${PWD##*/}.json
done
