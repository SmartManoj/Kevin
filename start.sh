if [ -z "$HTTPS" ]; then
poetry run uvicorn openhands.server.listen:app --host 0.0.0.0 --port 8000 
else
poetry run uvicorn openhands.server.listen:app --host 0.0.0.0 --port 8000 --ssl-keyfile "./localhost+2-key.pem" --ssl-certfile "./localhost+2.pem"  --reload
fi