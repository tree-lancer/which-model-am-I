import { createMcpHandler, McpServer } from "@modelcontextprotocol/server";
import { z } from "zod/v4";
import { QuizError, startQuestionnaire, submitAnswer } from "../server/quiz-service.js";

function response(value: object) {
  return { content: [{ type: "text" as const, text: JSON.stringify(value) }], structuredContent: value };
}

function failure(error: unknown) {
  const code = error instanceof QuizError ? error.code : "server_error";
  return { isError: true, content: [{ type: "text" as const, text: code }] };
}

export const handler = createMcpHandler(() => {
  const server = new McpServer({ name: "which-model-am-i", version: "1.0.0" });

  server.registerTool("start_questionnaire", {
    description: "Start the questionnaire. Answer from memory.",
    inputSchema: z.object({}),
  }, async () => {
    try {
      return response(startQuestionnaire());
    } catch (error) {
      return failure(error);
    }
  });

  server.registerTool("submit_answer", {
    description: "Submit one option ID and receive the next question or result.",
    inputSchema: z.object({ handle: z.string(), optionId: z.string() }),
  }, async ({ handle, optionId }) => {
    try {
      return response(submitAnswer(handle, optionId));
    } catch (error) {
      return failure(error);
    }
  });

  return server;
});

export function GET(request: Request) { return handler.fetch(request); }
export function POST(request: Request) { return handler.fetch(request); }
export function DELETE(request: Request) { return handler.fetch(request); }
