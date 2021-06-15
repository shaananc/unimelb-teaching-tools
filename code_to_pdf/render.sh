#!/usr/bin/env bash

# This code recurses into the given subdirectory looking for .c files, and from them produces a PDF of the code that can be annotated by tutors
# It currently supports only one .c file per student subdirectory

if [[ $# -ne 1 ]]; then
    echo "Usage: render.sh <directory-containing-subdirectories-of-student-c-code>"
    exit 2
fi

shopt -s globstar
for i in $1/**/*.c; do # Whitespace-safe and recursive
    echo $i
    render50 --size="A4 portrait" -o $(dirname $i)/program.pdf "./$i"
done
