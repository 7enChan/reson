#!/bin/sh

echo "Starting entrypoint script..."

if [ $# -eq 0 ]; then
    echo "No arguments provided. Executing Streamlit WebUI"
    exec python3 -m streamlit run /app_src/main_streamlit.py --server.address 0.0.0.0 --server.port 8501
elif [ "${1#--server.}" != "$1" ]; then
    echo "Executing Streamlit WebUI with server options: $@"
    exec python3 -m streamlit run /app_src/main_streamlit.py "$@"
elif [ "$1" = "python3" ] || [ "$1" = "python" ]; then
    # If the first argument is python or python3, execute the user-specified command
    echo "Executing user-specified python command: $@"
    exec "$@"
elif [ "$1" = "streamlit" ]; then
    echo "Executing user-specified Streamlit command: $@"
    exec "$@"
else
    # Otherwise, execute the default python3 /app_src/main.py command with all arguments
    echo "Executing default command: python3 /app_src/main.py $@"
    exec python3 /app_src/main.py "$@"
fi
