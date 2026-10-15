# Which Model Am I?

[![许可证：MIT](https://img.shields.io/badge/License-MIT-2d6a4f.svg)](LICENSE) [![技能：compile-questionnaire](https://img.shields.io/badge/Skills-compile--questionnaire-6f42c1.svg)](skills/compile-questionnaire/SKILL.md) [![问卷：v1.2.0](https://img.shields.io/badge/Questionnaire-v1.2.0-0969da.svg)](data/questionnaires/1.2.0/questionnaire.json) [![English](https://img.shields.io/badge/README-English-d73a49.svg)](README.md)

使用中转站的，从 github 上检索来的、反代来的, 甚至官方提供的 API Key, 都不可避免地遇到降智、路由到落后模型的问题。不要发现它，直到它把你的工作搞砸。

本项目用一份静态问卷来测试模型的离线知识截止日期，从而估计 AI Agent/中转站/API key 背后真正使用的基础模型。

💡本项目依赖具有 Computer use/浏览器访问和操作的 AI Agent, 如 [codex](https://chatgpt.com/codex), [claude code](https://claude.ai/) 等。cli Agent 待支持。

## 在线使用
直接让 AI Agent 访问 https://wmai-five.vercel.app/ ，无搜索/推测，凭记忆回答。

## 本地运行

```sh
uv sync
pnpm install
pnpm dev
```

让 AI Agent 打开页面，凭记忆回答。每个答案都会缩小日期区间；结果会对匹配的模型排序。

## 更新

按照[问卷编译技能](skills/compile-questionnaire/SKILL.md)操作。[知识截止日期目录](data/model_cutoffs.parquet)和[按版本保存的问卷](data/questionnaires/)是源数据。部署前运行 `pnpm build`。

## 支持的模型提供商

|  | 提供商 |  | 提供商 |
| :---: | --- | :---: | --- |
| <img src="src/assets/providers/alibaba.svg" alt="" width="28" height="28"> | Alibaba | <img src="src/assets/providers/anthropic.svg" alt="" width="28" height="28"> | Anthropic |
| <img src="src/assets/providers/deepseek.svg" alt="" width="28" height="28"> | DeepSeek | <img src="src/assets/providers/google.svg" alt="" width="28" height="28"> | Google |
| <img src="src/assets/providers/moonshot.svg" alt="" width="28" height="28"> | Moonshot | <img src="src/assets/providers/openai.svg" alt="" width="28" height="28"> | OpenAI |
| <img src="src/assets/providers/zhipu.svg" alt="" width="28" height="28"> | Zhipu |  |  |
