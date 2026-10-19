export type Answer = { questionId: string; optionId: string };
export type Question = { id: string; eventDate: string; correctOptionId: string; unknownOptionId: string };
export type Node = { type: string; questions?: Question[] };
export type Model = { provider: string; modelId: string; cutoff: string; basis: string; evidenceUrl: string };

function bounds(expression: string): [string | null, string | null] {
  const dates = expression.match(/\d{4}-\d{2}-\d{2}/g) || [];
  const first = dates[0];
  if (!first) throw new Error(`Invalid cutoff: ${expression}`);
  if (expression.startsWith("=")) return [first, first];
  if (expression.startsWith(">") && expression.includes("&<") && dates[1]) return [nextDay(first), previousDay(dates[1])];
  if (expression.startsWith(">")) return [nextDay(first), null];
  if (expression.startsWith("<")) return [null, previousDay(first)];
  throw new Error(`Invalid cutoff: ${expression}`);
}

function shiftDay(value: string, delta: number): string {
  const date = new Date(`${value}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + delta);
  return date.toISOString().slice(0, 10);
}

const nextDay = (value: string) => shiftDay(value, 1);
const previousDay = (value: string) => shiftDay(value, -1);

export function infer(answers: Answer[], nodes: Record<string, Node>, catalog: Model[]) {
  const questions = new Map<string, Question>();
  for (const node of Object.values(nodes)) {
    for (const question of node.questions || []) questions.set(question.id, question);
  }
  const observations = answers.map((answer) => ({ question: questions.get(answer.questionId)!, optionId: answer.optionId }));
  const knownDates = observations
    .filter(({ question, optionId }) => optionId === question.correctOptionId)
    .map(({ question }) => question.eventDate);
  const from = knownDates.length ? knownDates.sort().at(-1)! : null;
  const unknownDates = observations
    .filter(({ question, optionId }) => optionId === question.unknownOptionId && (!from || question.eventDate > from))
    .map(({ question }) => question.eventDate)
    .sort();
  const through = unknownDates.length ? previousDay(unknownDates[0]) : null;
  const matches = catalog.filter((model) => {
    if (model.basis === "release_date_upper_bound") return false;
    const [lower, upper] = bounds(model.cutoff);
    return (!from || !upper || upper >= from) && (!through || !lower || lower <= through);
  }).sort((left, right) => {
    const width = (model: Model) => {
      const [lower, upper] = bounds(model.cutoff);
      return lower && upper ? Date.parse(upper) - Date.parse(lower) : Number.POSITIVE_INFINITY;
    };
    return width(left) - width(right) || left.provider.localeCompare(right.provider) || left.modelId.localeCompare(right.modelId);
  });
  const excluded = through ? catalog.filter((model) => {
    if (model.basis === "release_date_upper_bound") return false;
    const [lower] = bounds(model.cutoff);
    return lower !== null && lower > through;
  }).sort((left, right) => {
    const [leftLower] = bounds(left.cutoff);
    const [rightLower] = bounds(right.cutoff);
    return leftLower!.localeCompare(rightLower!) || left.provider.localeCompare(right.provider) || left.modelId.localeCompare(right.modelId);
  }) : [];
  return { from, through, matches: matches as Model[], excluded: excluded as Model[], hasUnknownUpper: unknownDates.length > 0 };
}
