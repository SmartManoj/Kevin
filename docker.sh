docker pull ghcr.io/smartmanoj/kevin-sandbox:kevin-nikolaik

docker run  -it --pull=always \
    -e SANDBOX_RUNTIME_CONTAINER_IMAGE=ghcr.io/smartmanoj/kevin-sandbox:kevin-nikolaik \
    -e LOG_ALL_EVENTS=true \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v ~/.kevin-state:/.kevin-state \
    -p 8000:8000 \
    --env-file .env \
    --add-host host.docker.internal:host-gateway \
    ghcr.io/smartmanoj/kevin-app:kevin \
    /bin/sh -c "pip install itsdangerous && uvicorn openhands.server.listen:app --host 0.0.0.0 --port 8000"