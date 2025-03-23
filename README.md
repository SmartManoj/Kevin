### 📢 Announcement

Three airline companies operate flights from Dodola island. Each company has a different schedule of departures. The first company departs every 100 days, the second every 120 days and the third every 150 days. What is the greatest positive integer d for which it is true that there will be d consecutive days without a flight from Dodola island, regardless of the departure times of the various airlines?

Checkout [AI Mathematical Olympiad - Progress Prize 2](https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-2)

It is a $10mn fund to spur the open development of AI models.

---

Vision of this fork: Leverage SLMs effectively.

The easiest way to run Kevin is to press comma (,) to [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://github.com/codespaces/new/SmartManoj/Kevin) [120 hours free / month]

---

### [Refined SWE Bench Verified Lite](evaluation/benchmarks/swe_bench/Refined_SWE_BENCH.md)

Gemini Models solves all 93 issues in this category. Checkout the results [here](evaluation/benchmarks/swe_bench/swe_bench_verified_lite_result.md)

 ID: `sympy__sympy-22714`
 [openai/nvidia/llama-3.1-nemotron-70b-instruct](https://www.all-hands.dev/share?share_id=95f9ada5e76b767a07018497a412f876f5ffbe5debb578bcc72d52ab1036555f)

---


### Sample Examples

 1) Create an application in flask that can convert AWS cloudformation stack format from json to yaml and use curl to test ; don't do anything extra please.
 [groq/llama3-8b-8192](https://www.all-hands.dev/share?share_id=870d002486313bbbff706d62376412930ab6c95384dbb3d5c35205acdc946c3f)

 2) Gather S&P500 daily OHLC data for 1d and print it's close.
[openrouter/qwen/qwen-2.5-coder-32b-instruct](https://www.all-hands.dev/share?share_id=bb050c605e8e7316a2da1f8aea18c52362dc4588906b04a634efab57e5dc34ca), [openrouter/google/gemma-2-27b-it:free](https://www.all-hands.dev/share?share_id=9d856bbfae61a62017b1e737fa2a802d69efd080047d87f41db3dabb883801c0), [openrouter/meta-llama/llama-3.2-11b-vision-instruct](https://www.all-hands.dev/share?share_id=626abc444d0053663d4fd3ebe15fe0ed45a4247a08b873e2ec1b0bb542e0033c), [openrouter/microsoft/phi-3-medium-128k-instruct](https://www.all-hands.dev/share?share_id=f44bbd7ebcf4c4e4735f363663dac537d629dbfd486c5013d84ec40e12cc5851)

---

### Kevin Changelogs:
  [Integrated web browser using undetected-chromedriver ](https://github.com/SmartManoj/Kevin/commit/07a6e6e09deec59527dab824a9ad45b77cd57ced)

  [Added Custom Instructions](https://github.com/SmartManoj/Kevin/commit/2ae6a8ee368c9d9fa51d57d5120df0c6f50e5db3),

  [Added EC2 Runtime](https://github.com/SmartManoj/Kevin/commit/37d3fab5f58aa939d0689c6559325007e3f001c5),
  [Added Local Runtime](https://github.com/SmartManoj/Kevin/commit/07c7d10299313085c3f724494c05d252d2218326),

  [Added Auto Mode](https://github.com/All-Hands-AI/OpenHands/pull/2782),

  [Added Persistent sandbox](https://github.com/SmartManoj/Kevin/commit/2200b21dd01ecf3618d7e676cf16f875c5fce154),

  [Feat: Regenerate last message](https://github.com/SmartManoj/Kevin/commit/be74f0685c21cb8e6fc318a171676645c2f6ab6a),

  [Feat: Input Box for Notebook](https://github.com/SmartManoj/Kevin/commit/46651deeb7d4a2109f0afab0d4bbd33ba755f040),

  [Add litellm caching](https://github.com/SmartManoj/Kevin/commit/092f0077c843dd873cbb4acfd6d20f5e07b32912)

  And many more...


---

<a name="readme-top"></a>

<div align="center">
  <img src="frontend/public/logo.png" alt="Logo" width="200">
  <h1 align="center">Kevin: Code Quick, Create Fast</h1>
</div>


<div align="center">
  <a href="https://join.slack.com/t/openhands-ai/shared_invite/zt-2vbfigwev-G03twSpXaErwzYVD4CFiBg"><img src="https://img.shields.io/badge/Slack-Join%20Us-red?logo=slack&logoColor=white&style=for-the-badge" alt="Join our Slack community"></a>
  <a href="https://discord.gg/ESHStjSjD4"><img src="https://img.shields.io/badge/Discord-Join%20Us-purple?logo=discord&logoColor=white&style=for-the-badge" alt="Join our Discord community"></a>
  <a href="https://docs.all-hands.dev/modules/usage/getting-started"><img src="https://img.shields.io/badge/Documentation-000?logo=googledocs&logoColor=FFE165&style=for-the-badge" alt="Check out the documentation"></a>
  <hr>
</div>

Welcome to Kevin a fork of OpenHands (formerly OpenDevin), a platform for software development agents powered by AI.

Kevin can do anything a human developer does like modify code, run commands, browse the web,
call APIs, and yes—even copy code snippets from StackOverflow.

Learn more at [docs.all-hands.dev](https://docs.all-hands.dev), or jump to the [Quick Start](#-quick-start).

## ⚡ Quick Start

```bash
git clone https://github.com/SmartManoj/Kevin
cd Kevin
make build
make run
```

Visit [Development Guide](https://github.com/All-Hands-AI/OpenHands/blob/main/Development.md) for more information and setup instructions.

For Ollama, Visit [Local LLMs](https://docs.all-hands.dev/modules/usage/llms/local-llms) for more information and setup instructions.


FAQs:

How should one set config variables when using docker?

It can be set using env variables in the <GROUP_NAME>_<VARIABLE_NAME> format in uppercase.

---

### Upstream Readme:

<a name="readme-top"></a>

<div align="center">
  <h1 align="center">OpenHands: Code Less, Make More</h1>
</div>


<div align="center">
  <a href="https://github.com/All-Hands-AI/OpenHands/graphs/contributors"><img src="https://img.shields.io/github/contributors/All-Hands-AI/OpenHands?style=for-the-badge&color=blue" alt="Contributors"></a>
  <a href="https://github.com/All-Hands-AI/OpenHands/stargazers"><img src="https://img.shields.io/github/stars/All-Hands-AI/OpenHands?style=for-the-badge&color=blue" alt="Stargazers"></a>
  <a href="https://codecov.io/github/All-Hands-AI/OpenHands?branch=main"><img alt="CodeCov" src="https://img.shields.io/codecov/c/github/All-Hands-AI/OpenHands?style=for-the-badge&color=blue"></a>
  <a href="https://github.com/All-Hands-AI/OpenHands/blob/main/LICENSE"><img src="https://img.shields.io/github/license/All-Hands-AI/OpenHands?style=for-the-badge&color=blue" alt="MIT License"></a>
  <br/>
  <a href="https://join.slack.com/t/openhands-ai/shared_invite/zt-2ngejmfw6-9gW4APWOC9XUp1n~SiQ6iw"><img src="https://img.shields.io/badge/Slack-Join%20Us-red?logo=slack&logoColor=white&style=for-the-badge" alt="Join our Slack community"></a>
  <a href="https://discord.gg/ESHStjSjD4"><img src="https://img.shields.io/badge/Discord-Join%20Us-purple?logo=discord&logoColor=white&style=for-the-badge" alt="Join our Discord community"></a>
  <a href="https://github.com/All-Hands-AI/OpenHands/blob/main/CREDITS.md"><img src="https://img.shields.io/badge/Project-Credits-blue?style=for-the-badge&color=FFE165&logo=github&logoColor=white" alt="Credits"></a>
  <br/>
  <a href="https://docs.all-hands.dev/modules/usage/getting-started"><img src="https://img.shields.io/badge/Documentation-000?logo=googledocs&logoColor=FFE165&style=for-the-badge" alt="Check out the documentation"></a>
  <a href="https://arxiv.org/abs/2407.16741"><img src="https://img.shields.io/badge/Paper%20on%20Arxiv-000?logoColor=FFE165&logo=arxiv&style=for-the-badge" alt="Paper on Arxiv"></a>
  <a href="https://huggingface.co/spaces/OpenHands/evaluation"><img src="https://img.shields.io/badge/Benchmark%20score-000?logoColor=FFE165&logo=huggingface&style=for-the-badge" alt="Evaluation Benchmark Score"></a>
  <hr>
</div>

Welcome to OpenHands (formerly OpenDevin), a platform for software development agents powered by AI.

OpenHands agents can do anything a human developer can: modify code, run commands, browse the web,
call APIs, and yes—even copy code snippets from StackOverflow.

Learn more at [docs.all-hands.dev](https://docs.all-hands.dev), or jump to the [Quick Start](#-quick-start).

> [!IMPORTANT]
> Using OpenHands for work? We'd love to chat! Fill out
> [this short form](https://docs.google.com/forms/d/e/1FAIpQLSet3VbGaz8z32gW9Wm-Grl4jpt5WgMXPgJ4EDPVmCETCBpJtQ/viewform)
> to join our Design Partner program, where you'll get early access to commercial features and the opportunity to provide input on our product roadmap.

![App screenshot](./docs/static/img/screenshot.png)

## ⚡ Quick Start

The easiest way to run OpenHands is in Docker.
See the [Running OpenHands](https://docs.all-hands.dev/modules/usage/installation) guide for
system requirements and more information.

```bash
docker pull docker.all-hands.dev/all-hands-ai/runtime:0.29-nikolaik

docker run -it --rm --pull=always \
    -e SANDBOX_RUNTIME_CONTAINER_IMAGE=docker.all-hands.dev/all-hands-ai/runtime:0.29-nikolaik \
    -e LOG_ALL_EVENTS=true \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v ~/.openhands-state:/.openhands-state \
    -p 3000:3000 \
    --add-host host.docker.internal:host-gateway \
    --name openhands-app \
    docker.all-hands.dev/all-hands-ai/openhands:0.29
```

You'll find OpenHands running at [http://localhost:3000](http://localhost:3000)!

Finally, you'll need a model provider and API key.
[Anthropic's Claude 3.5 Sonnet](https://www.anthropic.com/api) (`anthropic/claude-3-5-sonnet-20241022`)
works best, but you have [many options](https://docs.all-hands.dev/modules/usage/llms).

---

You can also [connect OpenHands to your local filesystem](https://docs.all-hands.dev/modules/usage/runtimes#connecting-to-your-filesystem),
run OpenHands in a scriptable [headless mode](https://docs.all-hands.dev/modules/usage/how-to/headless-mode),
interact with it via a [friendly CLI](https://docs.all-hands.dev/modules/usage/how-to/cli-mode),
or run it on tagged issues with [a github action](https://docs.all-hands.dev/modules/usage/how-to/github-action).

Visit [Running OpenHands](https://docs.all-hands.dev/modules/usage/installation) for more information and setup instructions.

> [!CAUTION]
> OpenHands is meant to be run by a single user on their local workstation.
> It is not appropriate for multi-tenant deployments where multiple users share the same instance. There is no built-in isolation or scalability.
>
> If you're interested in running OpenHands in a multi-tenant environment, please
> [get in touch with us](https://docs.google.com/forms/d/e/1FAIpQLSet3VbGaz8z32gW9Wm-Grl4jpt5WgMXPgJ4EDPVmCETCBpJtQ/viewform)
> for advanced deployment options.

If you want to modify the OpenHands source code, check out [Development.md](https://github.com/All-Hands-AI/OpenHands/blob/main/Development.md).

Having issues? The [Troubleshooting Guide](https://docs.all-hands.dev/modules/usage/troubleshooting) can help.

## 📖 Documentation

To learn more about the project, and for tips on using OpenHands,
check out our [documentation](https://docs.all-hands.dev/modules/usage/getting-started).

There you'll find resources on how to use different LLM providers,
troubleshooting resources, and advanced configuration options.

## 🤝 How to Join the Community

OpenHands is a community-driven project, and we welcome contributions from everyone. We do most of our communication
through Slack, so this is the best place to start, but we also are happy to have you contact us on Discord or Github:

- [Join our Slack workspace](https://join.slack.com/t/openhands-ai/shared_invite/zt-2ngejmfw6-9gW4APWOC9XUp1n~SiQ6iw) - Here we talk about research, architecture, and future development.
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
