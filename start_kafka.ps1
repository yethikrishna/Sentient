<#
.SYNOPSIS
    Starts a fresh Kafka server inside WSL in a new terminal window.
.DESCRIPTION
    This script runs the following steps inside WSL (Ubuntu):
    - cd to the Kafka directory
    - generate a random Kafka cluster ID
    - format the Kafka storage
    - start the Kafka server
#>

# --- Configuration ---
$wslDistro = "Ubuntu"
$kafkaDirInWsl = "~/kafka_2.13-4.0.0"

# --- Kafka Command Sequence ---
$bashCommands = @"
cd $kafkaDirInWsl
KAFKA_CLUSTER_ID="\$(bin/kafka-storage.sh random-uuid)"
echo "Generated Kafka Cluster ID: \$KAFKA_CLUSTER_ID"
bin/kafka-storage.sh format --standalone -t \$KAFKA_CLUSTER_ID -c config/server.properties
bin/kafka-server-start.sh config/server.properties
"@

# Turn into single line bash command (safe for passing into terminal)
$oneLiner = $bashCommands -replace "`r`n", " && "

# Launch new terminal window running the WSL Kafka sequence
Start-Process wt.exe -ArgumentList "wsl -d $wslDistro bash -c '$oneLiner'"
