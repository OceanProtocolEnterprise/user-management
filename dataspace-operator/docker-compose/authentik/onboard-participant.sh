#######################
# Onboard Participant Oauth Source
#######################

docker exec -it authentik-server python /scripts/dataspace_operator_add_participant.py --config /participant-configs/$1