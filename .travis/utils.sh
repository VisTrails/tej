run_lines(){
    while read line; do echo "$line"; sh -c "$line" || exit $?; done
}
