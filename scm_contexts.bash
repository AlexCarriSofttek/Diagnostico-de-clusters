#!/bin/bash

JSON_FILE="clusters.json"

jq -r '.[] | "\(.project_id) \(.cluster) \(.region)"' "$JSON_FILE" |
while read -r project_id cluster region; do

    echo "Obteniendo credenciales para $cluster en $project_id ($region)..."

    gcloud container clusters get-credentials "$cluster" \
        --project "$project_id" \
        --region "$region"
    
done

# considere que el json tiene una entrada por cluster y la estructura es 
#[{project_id:"pid",cluster:"cluster",region:"region"}]