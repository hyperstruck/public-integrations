import { strict as assert } from "node:assert";
import { describe, test } from "node:test";

import {
  DeclineReason,
  DeclineRequest,
  DistillRequest,
  EpisodeModel,
  LearningBoundaryApiFetchParamCreator,
  ObserveRequest,
  ReinforceRequest,
  ResolvePurpose,
  ResolveRequest,
} from "./api";

const fetchParams = LearningBoundaryApiFetchParamCreator();

const invalidPurposeRequest: ResolveRequest = {
  agent_name: "support-agent",
  run_id: "support-agent:invalid-purpose",
  goal: "Reject an open string purpose.",
  // @ts-expect-error ResolvePurpose must remain a closed generated enum.
  resolve_purpose: "human_inspection",
};
void invalidPurposeRequest;

function jsonBody(fetchArgs: {
  options: { body?: unknown };
}): Record<string, unknown> {
  assert.equal(typeof fetchArgs.options.body, "string");
  return JSON.parse(fetchArgs.options.body as string) as Record<
    string,
    unknown
  >;
}

describe("LearningBoundaryApi wire contract", () => {
  test("boundary requests send agent_name, never hosted agent_id", () => {
    const request: ResolveRequest = {
      agent_name: "support-agent",
      run_id: "support-agent:run-1",
      goal: "Use prior learnings.",
      resolve_purpose: ResolvePurpose.ExplicitRecall,
    };
    const body = jsonBody(fetchParams.resolveEndpointResolvePost(request));

    assert.equal(body.agent_name, "support-agent");
    assert.equal(body.resolve_purpose, ResolvePurpose.ExplicitRecall);
    assert.equal(body.agent_id, undefined);
    assert.equal(body.agentName, undefined);
  });

  test("already-snake_case boundary inputs remain snake_case on the wire", () => {
    const episode: EpisodeModel = {
      run_id: "support-agent:run-1",
      goal: "Finish the task.",
      steps: [],
      outcome: {
        is_success: true,
        total_steps: 0,
        completed_steps: 0,
        failed_steps: 0,
      },
    };

    const bodies = [
      jsonBody(
        fetchParams.declineEndpointDeclinePost({
          agent_name: "support-agent",
          run_id: "support-agent:run-1",
          reason: DeclineReason.NoToolCalls,
          is_delivered: true,
        } satisfies DeclineRequest),
      ),
      jsonBody(
        fetchParams.distillEndpointDistillPost({
          agent_name: "support-agent",
          run_id: "distill:review-lessons",
          goal: "Extract review lessons.",
          evidence: [],
          outcome: { is_success: true, summary: "done" },
          max_learnings: 3,
        } satisfies DistillRequest),
      ),
      jsonBody(
        fetchParams.observeEndpointObservePost({
          agent_name: "support-agent",
          episode,
        } satisfies ObserveRequest),
      ),
      jsonBody(
        fetchParams.reinforceEndpointReinforcePost({
          agent_name: "support-agent",
          episode,
          is_org_promotion_allowed: false,
        } satisfies ReinforceRequest),
      ),
    ];

    for (const body of bodies) {
      assert.equal(body.agent_name, "support-agent");
      assert.equal(Object.keys(body).some((key) => /[A-Z]/.test(key)), false);
      assert.equal(body.agentName, undefined);
      assert.equal(body.agent_id, undefined);
    }
  });
});
