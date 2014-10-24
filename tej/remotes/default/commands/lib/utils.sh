absolutepathname(){
    cd "$(dirname "$1")"
    echo "$(pwd)/$(basename "$1")"
}
