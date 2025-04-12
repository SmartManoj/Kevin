# Use official Python image as base
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy application files
COPY remote_runtime_server.py .
COPY create_sandbox.py .
COPY deployment.yaml .
COPY service.yaml .

# install kubectl
RUN apt-get update && apt-get install -y curl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
RUN chmod +x ./kubectl
RUN mv ./kubectl /usr/local/bin/kubectl


# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn pydantic pyyaml

# Expose the port the app runs on
EXPOSE 12345

# Run the server
CMD ["python", "remote_runtime_server.py"]