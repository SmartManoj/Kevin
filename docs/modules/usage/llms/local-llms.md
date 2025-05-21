# Local LLMs

:::warning
When using a Local LLM, OpenHands may have limited functionality.
It is highly recommended that you use GPUs to serve local models for optimal experience.
:::

## News

- 2025/05/21: We collaborated with Mistral AI and released [Devstral Small](https://mistral.ai/news/devstral) that achieves [46.8% on SWE-Bench Verified](https://github.com/SWE-bench/experiments/pull/228)!
- 2025/03/31: We released an open model OpenHands LM v0.1 32B that achieves 37.1% on SWE-Bench Verified
([blog](https://www.all-hands.dev/blog/introducing-openhands-lm-32b----a-strong-open-coding-agent-model), [model](https://huggingface.co/all-hands/openhands-lm-32b-v0.1)).


## Quickstart: Running OpenHands on Your Macbook

### Serve the model on your Macbook

We recommend using [LMStudio](https://lmstudio.ai/) for serving these models locally.

1. Download [LM Studio](https://lmstudio.ai/) and install it

2. Download the model:
   - Option 1: Directly download the LLM from [this link](https://lmstudio.ai/model/devstral-small-2505-mlx) or by searching for the name `Devstral-Small-2505` in LM Studio
   - Option 2: Download a LLM in GGUF format. For example, to download [Devstral Small 2505 GGUF](https://huggingface.co/mistralai/Devstral-Small-2505_gguf), using `huggingface-cli download mistralai/Devstral-Small-2505_gguf --local-dir mistralai/Devstral-Small-2505_gguf`. Then in bash terminal, run `lms import {model_name}` in the directory where you've downloaded the model checkpoint (e.g. run `lms import devstralQ4_K_M.gguf` in `mistralai/Devstral-Small-2505_gguf`)

3. Open LM Studio application, you should first switch to `power user` mode, and then open the developer tab:
  
![image](./screenshots/1_select_power_user.png)

4. Then click `Select a model to load` on top of the application:

![image](./screenshots/2_select_model.png)

5. And choose the model you want to use, holding `option` on mac to enable advanced loading options:

![image](./screenshots/3_select_devstral.png)

6. You should then pick an appropriate context window for OpenHands based on your hardware configuration (larger than 32768 is recommended for using OpenHands, but too large may cause you to run out of memory); Flash attention is also recommended if it works on your machine.

![image](./screenshots/4_set_context_window.png)

7. And you should start the server (if it is not already in `Running` status), un-toggle `Serve on Local Network` and remember the port number of the LMStudio URL (`1234` is the port number for `http://127.0.0.1:1234` in this example):

![image](./screenshots/5_copy_url.png)

8. Finally, you can click the `copy` button near model name to copy the model name (`imported-models/uncategorized/devstralq4_k_m.gguf` in this example):

![image](./screenshots/6_copy_to_get_model_name.png)

### Start OpenHands with locally served model

Check [the installation guide](https://docs.all-hands.dev/modules/usage/installation) to make sure you have all the prerequisites for running OpenHands.

```bash
export LMSTUDIO_MODEL_NAME="imported-models/uncategorized/devstralq4_k_m.gguf" # <- Replace this with the model name you copied from LMStudio
export LMSTUDIO_URL="http://host.docker.internal:1234"  # <- Replace this with the port from LMStudio

docker pull docker.all-hands.dev/all-hands-ai/runtime:0.39-nikolaik

mkdir -p ~/.openhands-state && echo '{"language":"en","agent":"CodeActAgent","max_iterations":null,"security_analyzer":null,"confirmation_mode":false,"llm_model":"lm_studio/'$LMSTUDIO_MODEL_NAME'","llm_api_key":"dummy","llm_base_url":"'$LMSTUDIO_URL/v1'","remote_runtime_resource_factor":null,"github_token":null,"enable_default_condenser":true,"user_consents_to_analytics":true}' > ~/.openhands-state/settings.json

docker run -it --rm --pull=always \
    -e SANDBOX_RUNTIME_CONTAINER_IMAGE=docker.all-hands.dev/all-hands-ai/runtime:0.39-nikolaik \
    -e LOG_ALL_EVENTS=true \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v ~/.openhands-state:/.openhands-state \
    -p 3000:3000 \
    --add-host host.docker.internal:host-gateway \
    --name openhands-app \
    docker.all-hands.dev/all-hands-ai/openhands:0.39
```

Once your server is running -- you can visit `http://localhost:3000` in your browser to use OpenHands with local Devstral model:
```
Digest: sha256:e72f9baecb458aedb9afc2cd5bc935118d1868719e55d50da73190d3a85c674f
Status: Image is up to date for docker.all-hands.dev/all-hands-ai/openhands:0.39
Starting OpenHands...
Running OpenHands as root
14:22:13 - openhands:INFO: server_config.py:50 - Using config class None
INFO:     Started server process [8]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:3000 (Press CTRL+C to quit)
```


## Advanced: Serving LLM on GPUs

### Download model checkpoints

:::note
The model checkpoints downloaded here should NOT be in GGUF format.
:::

For example, to download [OpenHands LM 32B v0.1](https://huggingface.co/all-hands/openhands-lm-32b-v0.1):

```bash
huggingface-cli download all-hands/openhands-lm-32b-v0.1 --local-dir all-hands/openhands-lm-32b-v0.1
```

### Create an OpenAI-Compatible Endpoint With SGLang

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

### Create an OpenAI-Compatible Endpoint with vLLM

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

## Advanced: Run and Configure OpenHands

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
Once OpenHands is running, you'll need to set the following in the OpenHands UI through the Settings under the `LLM` tab: 
1. Enable `Advanced` options.
2. Set the following:
- `Custom Model` to `openai/<served-model-name>` (e.g. `openai/openhands-lm-32b-v0.1`)
- `Base URL` to `http://host.docker.internal:8000`
- `API key` to the same string you set when serving the model (e.g. `mykey`)
