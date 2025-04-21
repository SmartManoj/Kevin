# Local LLM with SGLang or vLLM

:::warning
When using a Local LLM, OpenHands may have limited functionality.
It is highly recommended that you use GPUs to serve local models for optimal experience.
:::

## News

- 2025/03/31: We released an open model OpenHands LM v0.1 32B that achieves 37.1% on SWE-Bench Verified
([blog](https://www.all-hands.dev/blog/introducing-openhands-lm-32b----a-strong-open-coding-agent-model), [model](https://huggingface.co/all-hands/openhands-lm-32b-v0.1)).

## Download the Model from Huggingface

For example, to download [OpenHands LM 32B v0.1](https://huggingface.co/all-hands/openhands-lm-32b-v0.1):

```bash
huggingface-cli download all-hands/openhands-lm-32b-v0.1 --local-dir all-hands/openhands-lm-32b-v0.1
```

## Create an OpenAI-Compatible Endpoint With a Model Serving Framework

### Serving with SGLang

- Install SGLang following [the official documentation](https://docs.sglang.ai/start/install.html).
- Example launch command for OpenHands LM 32B (with at least 2 GPUs):

```bash
SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN=1 python3 -m sglang.launch_server \
    --model all-hands/openhands-lm-32b-v0.1 \
    --served-model-name openhands-lm-32b-v0.1 \
    --port 8000 \
    --tp 2 --dp 1 \
    --host 0.0.0.0 \
    --api-key mykey --context-length 131072
```

### Serving with vLLM

- Install vLLM following [the official documentation](https://docs.vllm.ai/en/latest/getting_started/installation.html).
- Example launch command for OpenHands LM 32B (with at least 2 GPUs):

```bash
vllm serve all-hands/openhands-lm-32b-v0.1 \
    --host 0.0.0.0 --port 8000 \
    --api-key mykey \
    --tensor-parallel-size 2 \
    --served-model-name openhands-lm-32b-v0.1
    --enable-prefix-caching
```

## Run and Configure OpenHands

### Run OpenHands

#### Using Docker

Run OpenHands using [the official docker run command](../installation#start-the-app).

#### Using Development Mode

Use the instructions in [Development.md](https://github.com/All-Hands-AI/OpenHands/blob/main/Development.md) to build OpenHands.
Ensure `config.toml` exists by running `make setup-config` which will create one for you. In the `config.toml`, enter the following:

```
[core]
workspace_base="/path/to/your/workspace"

[llm]
model="openhands-lm-32b-v0.1"
ollama_base_url="http://localhost:8000"
```

Start OpenHands using `make run`.

### Configure OpenHands

In the OpenHands UI, click on the Settings wheel in the bottom-left corner.
Then in the `Model` input, enter `ollama/codellama:7b`, or the name of the model you pulled earlier.
If it doesn’t show up in the dropdown, enable `Advanced Settings` and type it in. Please note: you need the model name as listed by `ollama list`, with the prefix `ollama/`.

In the API Key field, enter `ollama` or any value, since you don't need a particular key.

In the Base URL field, enter `http://localhost:11434`.

And now you're ready to go!

## Configuring the ollama service (WSL) {#configuring-ollama-service-wsl-en}

The default configuration for ollama in WSL only serves localhost. This means you can't reach it from a docker container. eg. it wont work with OpenHands. First let's test that ollama is running correctly.

```bash
ollama list # get list of installed models
curl http://localhost:11434/api/generate -d '{"model":"[NAME]","prompt":"hi"}'
#ex. curl http://localhost:11434/api/generate -d '{"model":"codellama:7b","prompt":"hi"}'
#ex. curl http://localhost:11434/api/generate -d '{"model":"codellama","prompt":"hi"}' #the tag is optional if there is only one
```

Once that is done, test that it allows "outside" requests, like those from inside a docker container.

```bash
docker ps # get list of running docker containers, for most accurate test choose the OpenHands sandbox container.
docker exec [CONTAINER ID] curl http://host.docker.internal:11434/api/generate -d '{"model":"[NAME]","prompt":"hi"}'
#ex. docker exec cd9cc82f7a11 curl http://host.docker.internal:11434/api/generate -d '{"model":"codellama","prompt":"hi"}'
```

## Fixing it

Now let's make it work. Edit /etc/systemd/system/ollama.service with sudo privileges. (Path may vary depending on linux flavor)

```bash
sudo vi /etc/systemd/system/ollama.service
```

or

```bash
sudo nano /etc/systemd/system/ollama.service
```

In the [Service] bracket add these lines

```
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_ORIGINS=*"
```

Then save, reload the configuration and restart the service.

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

Finally test that ollama is accessible from within the container

```bash
ollama list # get list of installed models
docker ps # get list of running docker containers, for most accurate test choose the OpenHands sandbox container.
docker exec [CONTAINER ID] curl http://host.docker.internal:11434/api/generate -d '{"model":"[NAME]","prompt":"hi"}'
```


# Local LLM with LM Studio

Steps to set up LM Studio:
1. Open LM Studio
2. Go to the Local Server tab.
3. Click the "Start Server" button.
4. Select the model you want to use from the dropdown.


Set the following configs:
```bash
LLM_MODEL="openai/lmstudio"
LLM_BASE_URL="http://localhost:1234/v1"
CUSTOM_LLM_PROVIDER="openai"
```

### Docker

```bash
docker run # ...
    -e LLM_MODEL="openai/lmstudio" \
    -e LLM_BASE_URL="http://host.docker.internal:1234/v1" \
    -e CUSTOM_LLM_PROVIDER="openai" \
    # ...
```

You should now be able to connect to `http://localhost:3000/`

In the development environment, you can set the following configs in the `config.toml` file:

```
[core]
workspace_base="./workspace"

[llm]
model="openai/lmstudio"
base_url="http://localhost:1234/v1"
custom_llm_provider="openai"
```

Done! Now you can start OpenHands by: `make run` without Docker. You now should be able to connect to `http://localhost:3000/`

# Note

For WSL, run the following commands in cmd to set up the networking mode to mirrored:

```batch
python -c  "print('[wsl2]\nnetworkingMode=mirrored',file=open(r'%UserProfile%\.wslconfig','w'))"
wsl --shutdown
```
Once OpenHands is running, you'll need to set the following in the OpenHands UI through the Settings:
1. Enable `Advanced` options.
2. Set the following:
- `Custom Model` to `openai/<served-model-name>` (e.g. `openai/openhands-lm-32b-v0.1`)
- `Base URL` to `http://host.docker.internal:8000`
- `API key` to the same string you set when serving the model (e.g. `mykey`)
