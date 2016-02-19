absolutepathname(){
    prevdir="$PWD"
    cd "$(dirname "$1")"
    echo "$(pwd)/$(basename "$1")"
    cd "$prevdir"
}


format_timedelta(){
    total_secs=$1
    hours=$((total_secs / 3600))
    minutes=$(( (total_secs - hours * 3600) / 60 ))
    seconds=$((total_secs - hours * 3600 - minutes * 60))
    if [ ${#seconds} = 1 ]; then
        seconds=0${seconds}
    fi
    if [ "$hours" -gt 0 ]; then
        if [ ${#minutes} = 1 ]; then
            minutes=0${minutes}
        fi
        echo "$hours:$minutes:$seconds"
    else
        echo "$minutes:$seconds"
    fi
}
