absolutepathname(){
    prevdir="$PWD"
    cd "$(dirname "$1")"
    echo "$(pwd)/$(basename "$1")"
    cd "$prevdir"
}
