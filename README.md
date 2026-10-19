# Which Model Am I?

[![License: MIT](https://img.shields.io/badge/License-MIT-2d6a4f.svg)](LICENSE) [![Skills: compile-questionnaire](https://img.shields.io/badge/Skills-compile--questionnaire-6f42c1.svg)](skills/compile-questionnaire/SKILL.md) [![Questionnaire: v1.2.0](https://img.shields.io/badge/Questionnaire-v1.2.0-0969da.svg)](data/questionnaires/1.2.0/questionnaire.json) [![简体中文](https://img.shields.io/badge/README-%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-d73a49.svg)](README-zh.md)

Whether you use a relay service, an API key found on GitHub, a reverse proxy, or even an official API key, you can run into degraded responses or routing to an older model. Don't wait until it ruins your work to find out.

A static questionnaire that tests a model's offline knowledge cutoff to estimate the base model behind an AI Agent, relay service, or API key.

💡 This project requires an AI Agent with computer use or browser access and control, such as [Codex](https://chatgpt.com/codex) or [Claude Code](https://claude.ai/). Support for CLI agents is planned.

## Use online

Ask the AI Agent to visit https://wmai-five.vercel.app/ and answer from memory, without searching or guessing.

## Run locally

```sh
uv sync
pnpm install
pnpm dev
```

Let the AI agent open the page and answer from memory. Each answer narrows a date interval; the result ranks matching models.

## MCP

Set `WMAI_QUIZ_SECRET` to a random value of at least 32 bytes in Vercel's Production and Preview environment variables. The Streamable HTTP endpoint is `/api/mcp`. Run `pnpm test:mcp` to test it locally.

Generate a random 32-byte secret (64 hexadecimal characters):

```sh
openssl rand -hex 32
```

## Update

Follow [the compile skill](skills/compile-questionnaire/SKILL.md). The [cutoff catalog](data/model_cutoffs.parquet) and [versioned questionnaires](data/questionnaires/) are the source data. Run `pnpm build` before deployment.

## Supported model providers

|  | Provider |  | Provider |
| :---: | --- | :---: | --- |
| <img src="src/assets/providers/alibaba.svg" alt="" width="28" height="28"> | Alibaba | <img src="src/assets/providers/anthropic.svg" alt="" width="28" height="28"> | Anthropic |
| <img src="src/assets/providers/deepseek.svg" alt="" width="28" height="28"> | DeepSeek | <img src="src/assets/providers/google.svg" alt="" width="28" height="28"> | Google |
| <img src="src/assets/providers/moonshot.svg" alt="" width="28" height="28"> | Moonshot | <img src="src/assets/providers/openai.svg" alt="" width="28" height="28"> | OpenAI |
| <img src="src/assets/providers/zhipu.svg" alt="" width="28" height="28"> | Zhipu |  |  |
