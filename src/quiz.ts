import type { Answer } from "./inference-core";

export type Option = { id: string; label: string };
export type Question = {
  id: string;
  eventDate: string;
  prompt: string;
  options: Option[];
  correctOptionId: string;
  unknownOptionId: string;
};
export type Candidate = {
  provider: string;
  modelId: string;
  cutoff: string;
  basis: string;
  evidenceUrl: string;
  fit: number;
};
export type CheckpointNode = {
  type: "checkpoint";
  id: string;
  threshold: number;
  questions: Question[];
  next: { correct: string; incorrect: string };
};
export type ResultNode = {
  type: "result";
  id: string;
  range: { from: string | null; through: string | null };
  candidateCount: number;
  candidates: Candidate[];
};
export type Node = CheckpointNode | ResultNode;
export type Quiz = {
  version: string;
  asOf: string;
  catalogSize: number;
  questionCount: number;
  root: string;
  nodes: Record<string, Node>;
};
export type Position = { node: Node; questionIndex: number; checkpointDepth: number };

export function replay(quiz: Quiz, answers: Answer[]): Position | null {
  let node = quiz.nodes[quiz.root];
  let questionIndex = 0;
  let checkpointDepth = 0;
  let correctCount = 0;
  if (!node) return null;
  for (const answer of answers) {
    if (node.type !== "checkpoint") return null;
    const question = node.questions[questionIndex];
    if (!question || question.id !== answer.questionId || !question.options.some((option) => option.id === answer.optionId)) return null;
    correctCount += Number(answer.optionId === question.correctOptionId);
    questionIndex += 1;
    if (questionIndex === node.questions.length) {
      const next = quiz.nodes[node.next[correctCount >= node.threshold ? "correct" : "incorrect"]];
      if (!next) return null;
      node = next;
      questionIndex = 0;
      correctCount = 0;
      checkpointDepth += 1;
    }
  }
  return { node, questionIndex, checkpointDepth };
}

export function publicQuestion(question: Question) {
  return { id: question.id, prompt: question.prompt, options: question.options };
}
