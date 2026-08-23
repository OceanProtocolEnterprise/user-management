#######################
# Onboard Participant Oauth Source
#######################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "$1" ]; then
    echo "ERROR: No config filename provided."
    echo "Usage: $0 <config-filename>"
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/participant-configs/$1" ]; then
    echo "ERROR: Config file '/participant-configs/$1' not found."
    exit 1
fi


docker exec -it authentik-server python /scripts/dataspace_operator_add_participant.py --config /participant-configs/$1