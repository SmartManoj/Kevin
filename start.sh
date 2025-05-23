if [ -z "$HTTPS" ]; then
DEBUG=1 poetry run uvicorn openhands.server.listen:app --host 0.0.0.0 --port 8000 --reload
else
poetry run uvicorn openhands.server.listen:app --host 0.0.0.0 --port 8000 --ssl-keyfile "./localhost+2-key.pem" --ssl-certfile "./localhost+2.pem"  --reload
fi