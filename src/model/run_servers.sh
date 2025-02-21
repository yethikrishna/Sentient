#!/usr/bin/expect -f

set password "your_sudo_password" # Replace "your_sudo_password" with your actual sudo password
set base_dir "your/base/dir" # Replace "your/base/dir" with the actual path to the base directory of the project

# Run Agents Server
cd ${base_dir}/agents
spawn sudo -E <your-venv-path> -m uvicorn agents:app --host 0.0.0.0 --port 5001
expect "password for"
send "$password\r"
expect "*agents:app*"
interact

# Run App Server
cd ${base_dir}/app
spawn sudo -E <your-venv-path> -m uvicorn app:app --host 0.0.0.0 --port 5000
expect "password for"
send "$password\r"
expect "*app:app*"
interact

# Run Chat Server
cd ${base_dir}/chat
spawn sudo -E <your-venv-path> -m uvicorn chat:app --host 0.0.0.0 --port 5003
expect "password for"
send "$password\r"
expect "*chat:app*"
interact

# Run Common Server
cd ${base_dir}/common
spawn sudo -E <your-venv-path> -m uvicorn common:app --host 0.0.0.0 --port 5006
expect "password for"
send "$password\r"
expect "*common:app*"
interact

# Run Memory Server
cd ${base_dir}/memory
spawn sudo -E <your-venv-path> -m uvicorn memory:app --host 0.0.0.0 --port 5002
expect "password for"
send "$password\r"
expect "*memory:app*"
interact

# Run Scraper Server
cd ${base_dir}/scraper
spawn sudo -E <your-venv-path> -m uvicorn scraper:app --host 0.0.0.0 --port 5004
expect "password for"
send "$password\r"
expect "*scraper:app*"
interact

# Run Utils Server
cd ${base_dir}/utils
spawn sudo -E <your-venv-path> -m uvicorn utils:app --host 0.0.0.0 --port 5005
expect "password for"
send "$password\r"
expect "*utils:app*"
interact

# Run Auth Server
cd ${base_dir}/auth
spawn sudo -E <your-venv-path> -m uvicorn auth:app --host 0.0.0.0 --port 5007
expect "password for"
send "$password\r"
expect "*auth:app*"
interact