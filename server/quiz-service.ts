import { createHmac, timingSafeEqual } from "node:crypto";
import questionnaire from "../data/questionnaires/current.json" with { type: "json" };
import catalogJson from "../data/model_catalog.json" with { type: "json" };
import { infer, type Answer, type Model } from "../src/inference-core.js";
import { publicQuestion, replay, type Quiz } from "../src/quiz.js";

const quiz = questionnaire as Quiz;
const catalog = catalogJson as Model[];
const lifetimeMs = 2 * 60 * 60 * 1000;
const maxHandleLength = 8192;

type State = { version: string; answers: Answer[]; expiresAt: number };

export class QuizError extends Error {
  constructor(readonly code: string) {
    super(code);
  }
}

function secret(): string {
  const value = process.env.WMAI_QUIZ_SECRET;
  if (!value || Buffer.byteLength(value) < 32) throw new QuizError("server_not_configured");
  return value;
}

function signature(payload: string): Buffer {
  return createHmac("sha256", secret()).update(payload).digest();
}

function encode(state: State): string {
  const payload = Buffer.from(JSON.stringify(state)).toString("base64url");
  return `${payload}.${signature(payload).toString("base64url")}`;
}

function decode(handle: string): State {
  if (handle.length > maxHandleLength || !/^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(handle)) throw new QuizError("invalid_handle");
  const [payload, mac] = handle.split(".");
  const received = Buffer.from(mac, "base64url");
  const expected = signature(payload);
  if (received.toString("base64url") !== mac || received.length !== expected.length || !timingSafeEqual(received, expected)) {
    throw new QuizError("invalid_handle");
  }
  let state: State;
  try {
    state = JSON.parse(Buffer.from(payload, "base64url").toString("utf8"));
  } catch {
    throw new QuizError("invalid_handle");
  }
  if (state.version !== quiz.version || !Number.isSafeInteger(state.expiresAt) || state.expiresAt <= Date.now() ||
      !Array.isArray(state.answers) || state.answers.length > quiz.questionCount || !replay(quiz, state.answers)) {
    throw new QuizError("invalid_handle");
  }
  return state;
}

function next(state: State) {
  const position = replay(quiz, state.answers);
  if (!position) throw new QuizError("invalid_handle");
  if (position.node.type === "checkpoint") {
    return {
      status: "question" as const,
      version: quiz.version,
      answered: state.answers.length,
      handle: encode(state),
      question: publicQuestion(position.node.questions[position.questionIndex]),
    };
  }
  const estimate = infer(state.answers, quiz.nodes, catalog);
  return {
    status: "complete" as const,
    version: quiz.version,
    answered: state.answers.length,
    range: { from: estimate.from, through: estimate.through },
    upperBoundIsSoft: estimate.hasUnknownUpper,
    matches: estimate.matches,
    undated: estimate.undated,
    excluded: estimate.excluded,
  };
}

export function startQuestionnaire() {
  return next({ version: quiz.version, answers: [], expiresAt: Date.now() + lifetimeMs });
}

export function submitAnswer(handle: string, optionId: string) {
  const state = decode(handle);
  const position = replay(quiz, state.answers);
  if (!position || position.node.type !== "checkpoint") throw new QuizError("quiz_complete");
  const question = position.node.questions[position.questionIndex];
  if (!question.options.some((option) => option.id === optionId)) throw new QuizError("invalid_option");
  return next({ ...state, answers: [...state.answers, { questionId: question.id, optionId }] });
}
