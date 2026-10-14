import { useEffect, useState } from "react";
import questionnaire from "../data/questionnaires/current.json";
import { infer } from "./inference";
import alibabaIcon from "./assets/providers/alibaba.svg";
import anthropicIcon from "./assets/providers/anthropic.svg";
import deepseekIcon from "./assets/providers/deepseek.svg";
import googleIcon from "./assets/providers/google.svg";
import moonshotIcon from "./assets/providers/moonshot.svg";
import openaiIcon from "./assets/providers/openai.svg";
import zhipuIcon from "./assets/providers/zhipu.svg";

type Option = { id: string; label: string };
type Question = {
  id: string;
  eventDate: string;
  prompt: string;
  options: Option[];
  correctOptionId: string;
  unknownOptionId: string;
};
type Candidate = {
  provider: string;
  modelId: string;
  cutoff: string;
  basis: string;
  evidenceUrl: string;
  fit: number;
};
type CheckpointNode = {
  type: "checkpoint";
  id: string;
  threshold: number;
  questions: Question[];
  next: { correct: string; incorrect: string };
};
type ResultNode = {
  type: "result";
  id: string;
  range: { from: string | null; through: string | null };
  candidateCount: number;
  candidates: Candidate[];
};
type Node = CheckpointNode | ResultNode;
type Quiz = {
  version: string;
  asOf: string;
  catalogSize: number;
  questionCount: number;
  root: string;
  nodes: Record<string, Node>;
};
type Answer = { questionId: string; optionId: string };
type Position = { node: Node; questionIndex: number; checkpointDepth: number };

const quiz = questionnaire as Quiz;
const storageKey = `which-model-am-i:${quiz.version}`;
const providerInfo: Record<string, { label: string; icon: string }> = {
  Alibaba: { label: "阿里巴巴 · 通义千问", icon: alibabaIcon },
  Anthropic: { label: "Anthropic · Claude", icon: anthropicIcon },
  DeepSeek: { label: "DeepSeek", icon: deepseekIcon },
  Google: { label: "Google · Gemini", icon: googleIcon },
  Moonshot: { label: "月之暗面 · Kimi", icon: moonshotIcon },
  OpenAI: { label: "OpenAI", icon: openaiIcon },
  Zhipu: { label: "智谱 · GLM", icon: zhipuIcon },
};

function replay(answers: Answer[]): Position | null {
  let node = quiz.nodes[quiz.root];
  let questionIndex = 0;
  let checkpointDepth = 0;
  let correctCount = 0;
  for (const answer of answers) {
    if (node.type !== "checkpoint") return null;
    const question = node.questions[questionIndex];
    if (question.id !== answer.questionId || !question.options.some((option) => option.id === answer.optionId)) return null;
    correctCount += Number(answer.optionId === question.correctOptionId);
    questionIndex += 1;
    if (questionIndex === node.questions.length) {
      node = quiz.nodes[node.next[correctCount >= node.threshold ? "correct" : "incorrect"]];
      questionIndex = 0;
      correctCount = 0;
      checkpointDepth += 1;
    }
  }
  return { node, questionIndex, checkpointDepth };
}

function readAnswers(): Answer[] {
  try {
    const value = JSON.parse(localStorage.getItem(storageKey) || "null");
    if (!Array.isArray(value) || !replay(value)) return [];
    return value;
  } catch {
    return [];
  }
}

function formatRange(range: ResultNode["range"]): string {
  if (range.from && range.through) return `${range.from} ～ ${range.through}`;
  if (range.from) return `${range.from} 之后`;
  if (range.through) return `${range.through} 之前`;
  return "日期未确定";
}

function formatModelName(modelId: string): string {
  return modelId
    .replaceAll("-", " ")
    .replace(/^gpt\b/i, "GPT")
    .replace(/^glm\b/i, "GLM")
    .replace(/^qwen\b/i, "Qwen")
    .replace(/^claude\b/i, "Claude")
    .replace(/^gemini\b/i, "Gemini")
    .replace(/^deepseek\b/i, "DeepSeek")
    .replace(/^kimi\b/i, "Kimi");
}

export default function App() {
  const [answers, setAnswers] = useState<Answer[]>(readAnswers);
  const [selected, setSelected] = useState<string | null>(null);
  const position = replay(answers)!;
  const { node, questionIndex, checkpointDepth } = position;
  const estimate = node.type === "result" ? infer(answers, quiz.nodes) : null;
  const maxSteps = Math.ceil(Math.log2(quiz.questionCount / 3 + 1)) * 3;

  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(answers));
    } catch {
      return;
    }
  }, [answers]);

  function submit() {
    if (node.type !== "checkpoint" || selected === null) return;
    setAnswers((current) => [...current, { questionId: node.questions[questionIndex].id, optionId: selected }]);
    setSelected(null);
  }

  function back() {
    setAnswers((current) => current.slice(0, -1));
    setSelected(null);
  }

  function restart() {
    setAnswers([]);
    setSelected(null);
  }

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">知</span>
          <span>Which Model Am I?</span>
        </div>
        <span className="version">问卷 v{quiz.version}</span>
      </header>

      <main className="main">
        <div className="eyebrow"><span className="eyebrow-line" />{node.type === "checkpoint" ? "正在识别" : "识别完成"}</div>

        {node.type === "checkpoint" ? (
          <section className="card" aria-labelledby="question">
            <div className="card-topline">
              <span>第 {answers.length + 1} 题</span>
              <span>本轮核对 {questionIndex + 1} / {node.questions.length}</span>
            </div>
            <div className="progress-track" aria-hidden="true">
              <div className="progress-fill" style={{ width: `${Math.min(100, (answers.length / maxSteps) * 100)}%` }} />
            </div>
            <div className="question-number">问 · {String(answers.length + 1).padStart(2, "0")}</div>
            <h1 id="question">{node.questions[questionIndex].prompt}</h1>
            <p className="instruction">请凭已有知识选择答案，禁止搜索或查看网页源码。</p>
            <div className="options" role="radiogroup" aria-label="答案选项">
              {node.questions[questionIndex].options.map((option, index) => (
                <button
                  key={option.id}
                  type="button"
                  role="radio"
                  aria-checked={selected === option.id}
                  className={`option ${selected === option.id ? "selected" : ""} ${option.id === "unknown" ? "unknown" : ""}`}
                  onClick={() => setSelected(option.id)}
                >
                  <span className="option-letter" aria-hidden="true">{option.id === "unknown" ? "?" : String.fromCharCode(65 + index)}</span>
                  <span>{option.label}</span>
                  <span className="option-check" aria-hidden="true">{selected === option.id ? "✓" : ""}</span>
                </button>
              ))}
            </div>
            <div className="actions">
              <button type="button" className="text-button" onClick={back} disabled={answers.length === 0}>← 上一题</button>
              <button type="button" className="primary-button" onClick={submit} disabled={selected === null}>确认答案 <span aria-hidden="true">→</span></button>
            </div>
          </section>
        ) : (
          <section className="card result-card" aria-labelledby="result-title">
            <div className="result-symbol" aria-hidden="true">鉴</div>
            <p className="result-kicker">识别结果 · 共 {checkpointDepth} 轮核对</p>
            <h1 id="result-title">{estimate!.matches.length > 0 ? "可能的基础模型是" : "暂无匹配模型"}</h1>
            <div className="range-box">
              <span>知识截止日期之{estimate!.hasUnknownUpper ? "参考区间" : "下界"}</span>
              <strong>{formatRange(estimate!)}</strong>
            </div>
            {estimate!.matches.length > 0 && (
              <div className="candidate-list">
                {estimate!.matches.slice(0, 10).map((candidate, index) => {
                  const provider = providerInfo[candidate.provider];
                  return (
                    <div className="candidate" key={`${candidate.provider}:${candidate.modelId}`}>
                      <span className="candidate-rank">{String(index + 1).padStart(2, "0")}</span>
                      <span className="provider-icon">{provider ? <img src={provider.icon} alt="" /> : candidate.provider.slice(0, 1)}</span>
                      <div className="candidate-detail">
                        <span className="candidate-provider">{provider?.label || candidate.provider}</span>
                        <strong>{formatModelName(candidate.modelId)}</strong>
                        <span className="candidate-cutoff">知识日期 {candidate.cutoff}</span>
                      </div>
                      <a href={candidate.evidenceUrl} target="_blank" rel="noreferrer" aria-label={`查看 ${candidate.modelId} 的证据`}>来源 ↗</a>
                    </div>
                  );
                })}
              </div>
            )}
            {estimate!.matches.length > 10 && <p className="overflow-note">另有 {estimate!.matches.length - 10} 个有公开知识日期依据的候选模型未显示。</p>}
            {estimate!.excluded.length > 0 && (
              <section className="excluded-section" aria-labelledby="excluded-title">
                <h2 id="excluded-title">❌ 不可能是哪些模型· {estimate!.excluded.length}</h2>
                <div className="candidate-list">
                  {estimate!.excluded.map((candidate) => {
                    const provider = providerInfo[candidate.provider];
                    return (
                      <div className="candidate excluded" key={`${candidate.provider}:${candidate.modelId}`}>
                        <span className="candidate-rank" aria-label="不符合参考区间">❌</span>
                        <span className="provider-icon">{provider ? <img src={provider.icon} alt="" /> : candidate.provider.slice(0, 1)}</span>
                        <div className="candidate-detail">
                          <span className="candidate-provider">{provider?.label || candidate.provider}</span>
                          <strong>{formatModelName(candidate.modelId)}</strong>
                          <span className="candidate-cutoff">知识日期 {candidate.cutoff}</span>
                        </div>
                        <a href={candidate.evidenceUrl} target="_blank" rel="noreferrer" aria-label={`查看 ${candidate.modelId} 的证据`}>来源 ↗</a>
                      </div>
                    );
                  })}
                </div>
              </section>
            )}
            <div className="actions">
              <button type="button" className="text-button" onClick={back}>← 上一题</button>
              <button type="button" className="primary-button" onClick={restart}>重新开始 <span aria-hidden="true">→</span></button>
            </div>
          </section>
        )}
        <p className="footnote">请让需要识别的 AI Agent 自行浏览并完成问卷。</p>
      </main>

      <footer className="footer">
        <span>© Which Model Am I?</span>
        <span>{quiz.catalogSize} 个模型条目 · 更新至 {quiz.asOf}</span>
      </footer>
    </div>
  );
}
