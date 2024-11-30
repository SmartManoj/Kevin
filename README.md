### [Refined SWE BENCH Verified Lite](evaluation/benchmarks/swe_bench/Refined_SWE_BENCH.md)

Gemini Models solves all 93 issues in this category. Checkout the results at [evaluation\swe_bench\status.json](evaluation/benchmarks/swe_bench/status.json)

 ID: `sympy__sympy-22714`
 [openai/nvidia/llama-3.1-nemotron-70b-instruct](https://www.all-hands.dev/share?share_id=95f9ada5e76b767a07018497a412f876f5ffbe5debb578bcc72d52ab1036555f)

---


The easiest way to run Kevin is to [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://github.com/codespaces/new/SmartManoj/Kevin) 🔥🔥🔥


The vision is to leverage SLMs effectively and work towards solving most of the issues on the SWE-Bench Lite evaluation.

### Sample Examples using `groq/llama3-8b-8192`

 1) Create an application in flask that can convert AWS cloudformation stack format from json to yaml and use curl to test ; don't do anything extra please.
 [Event history link](https://www.all-hands.dev/share?share_id=870d002486313bbbff706d62376412930ab6c95384dbb3d5c35205acdc946c3f)


To be updated:



### Kevin Changelogs:

  Oct 2, 2024: [Added EC2 Runtime](https://github.com/SmartManoj/Kevin/commit/37d3fab5f58aa939d0689c6559325007e3f001c5)

  1) [Added Auto Mode](https://github.com/All-Hands-AI/OpenHands/pull/2782) 🔥🔥🔥
  2) [Restarted Jupyter kernel if package installed via bash too](https://github.com/All-Hands-AI/OpenHands/pull/3178) 👍
  3) [Cleaned Browser Observattions](https://github.com/All-Hands-AI/OpenHands/pull/3096) 🧹
  4) [Showed relevant error in UI](https://github.com/All-Hands-AI/OpenHands/pull/2657) 🚨
  5) [Added Event History Condenser](https://github.com/All-Hands-AI/OpenHands/pull/2937) 📜
  6) [Feat: Persist sandbox for Event Runtime](https://github.com/SmartManoj/Kevin/commit/2200b21dd01ecf3618d7e676cf16f875c5fce154) 🥳🥳
  7) [Parsed pip output and restarted kernel automatically (for bash too)](https://github.com/SmartManoj/Kevin/commit/3b77d5b2ec592e0fcb5bd7ed8a0d5787378bc0de) 📦
  8) [Added editable address bar in browser tab](https://github.com/All-Hands-AI/OpenHands/pull/3078) 🌐
  9) [Include workspace contents if any at first step only.](https://github.com/All-Hands-AI/OpenHands/pull/2865#issuecomment-2257487634) 📂
  10) [Add start and kill modes in Makefile](https://github.com/All-Hands-AI/OpenHands/pull/2850) 📳
  11) [Process interactive commands and stream output in logs](https://github.com/All-Hands-AI/OpenHands/pull/3042) 📜
  12) [Use execute tags for browsing agent too](https://github.com/SmartManoj/Kevin/commit/b2a02ce39295c33d00429937804cdd3e08d70969) 🏷️
  13) [Feat: Regenerate message](https://github.com/SmartManoj/Kevin/commit/be74f0685c21cb8e6fc318a171676645c2f6ab6a) 🔄
  14) [Feat: Editable Notebook](https://github.com/SmartManoj/Kevin/commit/46651deeb7d4a2109f0afab0d4bbd33ba755f040) 📝
  15) [Feat: Add docker to sandbox](https://github.com/SmartManoj/Kevin/commit/c145a4d6e9b080423af995f268b09c37ebc1184a) 🐳
  16) [UI: Enable right click to paste in terminal](https://github.com/All-Hands-AI/OpenHands/pull/3162) 🖱️
  17) [Added override UI settings configuration](https://github.com/SmartManoj/Kevin/pull/36) 🛠️
  18) [UI: Show Step Count](https://github.com/SmartManoj/Kevin/commit/78b89b510a7d40fe16022f407974cf765487881a) 📊
  19) [Import the event history upto specific steps](https://github.com/SmartManoj/Kevin/commit/7d9314fb79a78590f9612a374e700287584edbfb) 📜
  20) [Add litellm caching](https://github.com/SmartManoj/Kevin/commit/092f0077c843dd873cbb4acfd6d20f5e07b32912) 📦

### Bug Fixes:
  1) [Fixed GroqException - content must be a string for role system & assisstant](https://github.com/SmartManoj/Kevin/commit/30c98d458a299d789ebd6b8ada842c050bc91b20) 🛠️
  2) [Fixed GroqException - condense' is unsupported](https://github.com/SmartManoj/Kevin/commit/1ece04784beb657dccbf615b3085e72f23a73e77) 🛠️
  3) [Clear history when starting a new task](https://github.com/SmartManoj/Kevin/commit/f874e13fdd4ea50dcd0d8484639de40a1d6f66f4) 🧹
  4) [Add miniforge path to synchronize bash and notebook](https://github.com/SmartManoj/Kevin/commit/6753d8b2b2b4e5a753cc4b3e26982d36464b6002) 🛣️
  5) [Fixed frontend terminal prompt](https://github.com/SmartManoj/Kevin/commit/77950625b51a779b99533a9af616c97e640d5cd6) 🛠️
  6) [Set TERM variable in bash](https://github.com/SmartManoj/Kevin/ec84c3b633ac23effac9f096a68560abc7388d2f) 🛠️

### Minor Changes:
  1) [Notify after task is finished](https://github.com/SmartManoj/Kevin/commit/cec8e7d9af109efc6abb099e2f9ac5b42b6650f6) 📢

### Separate Feature Branches:
  1) [Added Tutor Agent](https://github.com/SmartManoj/Kevin/tree/add-tutor-agent) 🧑‍🏫
---

<a name="readme-top"></a>

<div align="center">
  <img src="./docs/static/img/logo.webp" alt="Logo" width="200">
  <h1 align="center">Kevin: Code Quick, Create Fast</h1>
</div>


<div align="center">
  <a href="https://github.com/All-Hands-AI/OpenHands/graphs/contributors"><img src="https://img.shields.io/github/contributors/All-Hands-AI/OpenHands?style=for-the-badge&color=blue" alt="Contributors"></a>
  <a href="https://github.com/All-Hands-AI/OpenHands/stargazers"><img src="https://img.shields.io/github/stars/All-Hands-AI/OpenHands?style=for-the-badge&color=blue" alt="Stargazers"></a>
  <a href="https://codecov.io/github/All-Hands-AI/OpenHands?branch=main"><img alt="CodeCov" src="https://img.shields.io/codecov/c/github/All-Hands-AI/OpenHands?style=for-the-badge&color=blue"></a>
  <a href="https://github.com/All-Hands-AI/OpenHands/blob/main/LICENSE"><img src="https://img.shields.io/github/license/All-Hands-AI/OpenHands?style=for-the-badge&color=blue" alt="MIT License"></a>
  <br/>
  <a href="https://join.slack.com/t/openhands-ai/shared_invite/zt-2tom0er4l-JeNUGHt_AxpEfIBstbLPiw"><img src="https://img.shields.io/badge/Slack-Join%20Us-red?logo=slack&logoColor=white&style=for-the-badge" alt="Join our Slack community"></a>
  <a href="https://discord.gg/ESHStjSjD4"><img src="https://img.shields.io/badge/Discord-Join%20Us-purple?logo=discord&logoColor=white&style=for-the-badge" alt="Join our Discord community"></a>
  <a href="https://github.com/All-Hands-AI/OpenHands/blob/main/CREDITS.md"><img src="https://img.shields.io/badge/Project-Credits-blue?style=for-the-badge&color=FFE165&logo=github&logoColor=white" alt="Credits"></a>
  <br/>
  <a href="https://docs.all-hands.dev/modules/usage/getting-started"><img src="https://img.shields.io/badge/Documentation-000?logo=googledocs&logoColor=FFE165&style=for-the-badge" alt="Check out the documentation"></a>
  <a href="https://arxiv.org/abs/2407.16741"><img src="https://img.shields.io/badge/Paper%20on%20Arxiv-000?logoColor=FFE165&logo=arxiv&style=for-the-badge" alt="Paper on Arxiv"></a>
  <a href="https://huggingface.co/spaces/OpenHands/evaluation"><img src="https://img.shields.io/badge/Benchmark%20score-000?logoColor=FFE165&logo=huggingface&style=for-the-badge" alt="Evaluation Benchmark Score"></a>
  <hr>
</div>

Welcome to Kevin a fork of OpenHands (formerly OpenDevin), a platform for software development agents powered by AI.

Kevin can do anything a human developer can: modify code, run commands, browse the web,
call APIs, and yes—even copy code snippets from StackOverflow.

Learn more at [docs.all-hands.dev](https://docs.all-hands.dev), or jump to the [Quick Start](#-quick-start).

![App screenshot](./docs/static/img/screenshot.png)

## ⚡ Quick Start

The easiest way to run OpenHands is in Docker.
See the [Installation](https://docs.all-hands.dev/modules/usage/installation) guide for
system requirements and more information.

```bash
docker pull docker.all-hands.dev/all-hands-ai/runtime:0.14-nikolaik

docker run -it --pull=always \
    -e SANDBOX_USE_HOST_NETWORK=true \
    -e SANDBOX_RUNTIME_CONTAINER_IMAGE=docker.all-hands.dev/all-hands-ai/runtime:0.14-nikolaik \
    -e LOG_ALL_EVENTS=true \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -p 3000:3000 \
    --add-host host.docker.internal:host-gateway \
    --name openhands-app \
    docker.all-hands.dev/all-hands-ai/openhands:0.14
```

You'll find OpenHands running at [http://localhost:3000](http://localhost:3000)!

Finally, you'll need a model provider and API key.
[Anthropic's Claude 3.5 Sonnet](https://www.anthropic.com/api) (`anthropic/claude-3-5-sonnet-20241022`)
works best, but you have [many options](https://docs.all-hands.dev/modules/usage/llms).

---

You can also [connect OpenHands to your local filesystem](https://docs.all-hands.dev/modules/usage/runtimes),
run OpenHands in a scriptable [headless mode](https://docs.all-hands.dev/modules/usage/how-to/headless-mode),
interact with it via a [friendly CLI](https://docs.all-hands.dev/modules/usage/how-to/cli-mode),
or run it on tagged issues with [a github action](https://github.com/All-Hands-AI/OpenHands/blob/main/openhands/resolver/README.md).

Visit [Installation](https://docs.all-hands.dev/modules/usage/installation) for more information and setup instructions.

If you want to modify the Kevin source code, check out [Development.md](https://github.com/SmartManoj/Kevin/blob/main/Development.md).

Having issues? The [Troubleshooting Guide](https://docs.all-hands.dev/modules/usage/troubleshooting) can help.

## 📖 Documentation

To learn more about the project, and for tips on using OpenHands,
**check out our [documentation](https://docs.all-hands.dev/modules/usage/getting-started)**.

There you'll find resources on how to use different LLM providers,
troubleshooting resources, and advanced configuration options.

## 🤝 How to Join the Community

OpenHands is a community-driven project, and we welcome contributions from everyone. We do most of our communication
through Slack, so this is the best place to start, but we also are happy to have you contact us on Discord or Github:

- [Join our Slack workspace](https://join.slack.com/t/openhands-ai/shared_invite/zt-2tom0er4l-JeNUGHt_AxpEfIBstbLPiw) - Here we talk about research, architecture, and future development.
- [Join our Discord server](https://discord.gg/ESHStjSjD4) - This is a community-run server for general discussion, questions, and feedback.
- [Read or post Github Issues](https://github.com/All-Hands-AI/OpenHands/issues) - Check out the issues we're working on, or add your own ideas.

See more about the community in [COMMUNITY.md](./COMMUNITY.md) or find details on contributing in [CONTRIBUTING.md](./CONTRIBUTING.md).

## 📈 Progress

See the monthly OpenHands roadmap [here](https://github.com/orgs/All-Hands-AI/projects/1) (updated at the maintainer's meeting at the end of each month).

<p align="center">
  <a href="https://star-history.com/#All-Hands-AI/OpenHands&Date">
    <img src="https://api.star-history.com/svg?repos=All-Hands-AI/OpenHands&type=Date" width="500" alt="Star History Chart">
  </a>
</p>

## 📜 License

Distributed under the MIT License. See [`LICENSE`](./LICENSE) for more information.

## 🙏 Acknowledgements

OpenHands is built by a large number of contributors, and every contribution is greatly appreciated! We also build upon other open source projects, and we are deeply thankful for their work.

For a list of open source projects and licenses used in OpenHands, please see our [CREDITS.md](./CREDITS.md) file.

## 📚 Cite

```
@misc{openhands,
      title={{OpenHands: An Open Platform for AI Software Developers as Generalist Agents}},
      author={Xingyao Wang and Boxuan Li and Yufan Song and Frank F. Xu and Xiangru Tang and Mingchen Zhuge and Jiayi Pan and Yueqi Song and Bowen Li and Jaskirat Singh and Hoang H. Tran and Fuqiang Li and Ren Ma and Mingzhang Zheng and Bill Qian and Yanjun Shao and Niklas Muennighoff and Yizhe Zhang and Binyuan Hui and Junyang Lin and Robert Brennan and Hao Peng and Heng Ji and Graham Neubig},
      year={2024},
      eprint={2407.16741},
      archivePrefix={arXiv},
      primaryClass={cs.SE},
      url={https://arxiv.org/abs/2407.16741},
}
```
