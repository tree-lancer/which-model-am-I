import assert from "node:assert/strict";
import { test } from "node:test";
import { Client, StreamableHTTPClientTransport } from "@modelcontextprotocol/client";
import questionnaire from "../data/questionnaires/current.json";
import { handler } from "../api/mcp";
import { QuizError, startQuestionnaire, submitAnswer } from "../server/quiz-service";

process.env.WMAI_QUIZ_SECRET = "test-only-secret-with-at-least-thirty-two-characters";

const correctById = new Map(
  Object.values(questionnaire.nodes)
    .filter((node) => "questions" in node)
    .flatMap((node) => node.questions.map((question) => [question.id, question.correctOptionId] as const)),
);

test("MCP quiz completes the reported November 2025 path", async () => {
  const transport = new StreamableHTTPClientTransport(new URL("http://test.local/api/mcp"), {
    fetch: (url, init) => handler.fetch(new Request(url, init)),
  });
  const client = new Client({ name: "quiz-test", version: "1.0.0" }, { versionNegotiation: { mode: "auto" } });
  await client.connect(transport);
  try {
    const tools = await client.listTools();
    assert.deepEqual(tools.tools.map((tool) => tool.name).sort(), ["start_questionnaire", "submit_answer"]);

    let result = (await client.callTool({ name: "start_questionnaire", arguments: {} })).structuredContent as Record<string, any>;
    assert.equal(result.status, "question");
    assert.equal("correctOptionId" in result.question, false);
    assert.equal("sourceUrl" in result.question, false);

    const tampered = `${result.handle.slice(0, -1)}${result.handle.at(-1) === "A" ? "B" : "A"}`;
    const invalid = await client.callTool({ name: "submit_answer", arguments: { handle: tampered, optionId: "unknown" } });
    assert.equal(invalid.isError, true);
    assert.equal(invalid.content[0].type, "text");
    if (invalid.content[0].type === "text") assert.equal(invalid.content[0].text, "invalid_handle");

    const known = new Set(["texas_floods", "gpt5_launch", "nepal_protests", "melissa_jamaica", "cop30_fire"]);
    for (let count = 0; result.status === "question"; count += 1) {
      assert.ok(count < questionnaire.questionCount);
      const optionId = known.has(result.question.id) ? correctById.get(result.question.id)! : "unknown";
      result = (await client.callTool({ name: "submit_answer", arguments: { handle: result.handle, optionId } })).structuredContent as Record<string, any>;
    }
    assert.deepEqual(result.range, { from: "2025-11-20", through: "2025-11-25" });
    assert.equal(result.upperBoundIsSoft, true);
    assert.ok(result.excluded.some((model: { modelId: string }) => model.modelId === "claude-fable-5"));
    assert.equal(result.excluded.length, 19);

    const legacyTransport = new StreamableHTTPClientTransport(new URL("http://test.local/api/mcp"), {
      fetch: (url, init) => handler.fetch(new Request(url, init)),
    });
    const legacyClient = new Client({ name: "legacy-test", version: "1.0.0" });
    await legacyClient.connect(legacyTransport);
    try {
      const legacyStart = await legacyClient.callTool({ name: "start_questionnaire", arguments: {} });
      assert.equal((legacyStart.structuredContent as { status: string }).status, "question");
    } finally {
      await legacyClient.close();
    }
  } finally {
    await client.close();
    await handler.close();
  }
});

test("signed handles reject invalid options and expiration", () => {
  const first = startQuestionnaire();
  assert.equal(first.status, "question");
  assert.throws(() => submitAnswer(first.handle, "missing"), (error) => error instanceof QuizError && error.code === "invalid_option");
  const now = Date.now;
  try {
    Date.now = () => now() + 2 * 60 * 60 * 1000 + 1;
    assert.throws(() => submitAnswer(first.handle, "unknown"), (error) => error instanceof QuizError && error.code === "invalid_handle");
  } finally {
    Date.now = now;
  }
});
