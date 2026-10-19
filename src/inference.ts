import catalogRaw from "../data/model_catalog.json?raw";
import { infer as inferCore, type Answer, type Node, type Model } from "./inference-core";

const catalog: Model[] = JSON.parse(catalogRaw);

export function infer(answers: Answer[], nodes: Record<string, Node>) {
  return inferCore(answers, nodes, catalog);
}
