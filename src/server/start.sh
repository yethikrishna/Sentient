#!/bin/bash
# This script is the entrypoint for the container. It simply starts supervisord.

echo "Container starting... Launching supervisord."
/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf