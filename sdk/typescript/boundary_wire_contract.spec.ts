import {
  BoundaryAcceptedResponse,
  DeclineReason,
  DeclineRequest,
  DistillRequest,
  EpisodeModel,
  LearningBoundaryApiFetchParamCreator,
  ObligationClosureResult,
  ObserveRequest,
  ReinforceRequest,
  ResolvePurpose,
  ResolveRequest,
  ResolveResponse,
  RunDetailResponse,
  RunResponse,
  RunStatusResponse,
} from "./api";

declare function describe(name: string, fn: () => void): void;
declare function test(name: string, fn: () => void): void;
declare function expect(actual: unknown): {
  toBe(expected: unknown): void;
  toBeUndefined(): void;
};

const fetchParams = LearningBoundaryApiFetchParamCreator();

function jsonBody(fetchArgs: {
  options: { body?: unknown };
}): Record<string, unknown> {
  expect(typeof fetchArgs.options.body).toBe("string");
  return JSON.parse(fetchArgs.options.body as string) as Record<
    string,
    unknown
  >;
}

describe("LearningBoundaryApi wire contract", () => {
  test("run responses type client metadata separately from run state", () => {
    const clientMetadata: RunResponse["client_metadata"] = {
      external_ticket_id: "INC-2048",
    };
    const detailClientMetadata: RunDetailResponse["client_metadata"] =
      clientMetadata;

    expect(clientMetadata.external_ticket_id).toBe("INC-2048");
    expect(detailClientMetadata.external_ticket_id).toBe("INC-2048");
  });

  test("boundary requests send agent_name, never hosted agent_id", () => {
    const request: ResolveRequest = {
      agent_name: "support-agent",
      run_id: "support-agent:run-1",
      goal: "Use prior learnings.",
    };
    const body = jsonBody(fetchParams.resolveEndpointResolvePost(request));

    expect(body.agent_name).toBe("support-agent");
    expect(body.agent_id).toBeUndefined();
    expect(body.agentName).toBeUndefined();
  });

  test("a generated enum stays a closed set and reaches the wire as its value", () => {
    // The Python SDK asserts the opposite property (an unknown value deserialises to the raw
    // string rather than raising), so it cannot stand in for this one. Enum shape is the same
    // class of silent generator drift as property naming: a generator that re-emits this as a
    // bare string type, or renames its members, compiles clean and publishes a broken contract.
    const request: ResolveRequest = {
      agent_name: "support-agent",
      run_id: "support-agent:run-1",
      goal: "Use prior learnings.",
      resolve_purpose: ResolvePurpose.AgentLoop,
    };
    const body = jsonBody(fetchParams.resolveEndpointResolvePost(request));

    expect(ResolvePurpose.AgentLoop).toBe("agent_loop");
    expect(body.resolve_purpose).toBe("agent_loop");
    expect(body.resolvePurpose).toBeUndefined();
  });

  test("the obligation block's request controls reach the wire under their own names", () => {
    // ResolveRequest forbids unknown fields on the server, so a generator that renamed any of
    // these to camelCase would compile clean here and be rejected at runtime by every call that
    // used it. That is the failure this file exists to catch, and it is invisible to the type
    // checker alone.
    const request: ResolveRequest = {
      agent_name: "support-agent",
      run_id: "support-agent:run-1",
      goal: "Use prior learnings.",
      as_of: "2026-08-27T09:00:00+10:00",
      timezone: "Australia/Sydney",
      max_obligations: 3,
      obligation_horizon_days: 7,
    };
    const body = jsonBody(fetchParams.resolveEndpointResolvePost(request));

    expect(body.as_of).toBe("2026-08-27T09:00:00+10:00");
    expect(body.timezone).toBe("Australia/Sydney");
    expect(body.max_obligations).toBe(3);
    expect(body.obligation_horizon_days).toBe(7);
    expect(body.asOf).toBeUndefined();
    expect(body.maxObligations).toBeUndefined();
    expect(body.obligationHorizonDays).toBeUndefined();
  });

  test("the obligation block is a third response field, and every one stays optional", () => {
    // Optional in the generated type as well as in the schema: a consumer written against an
    // older server compiles unchanged, which is what makes adding a block additive rather than
    // a breaking release.
    const empty: ResolveResponse = {};
    const served: ResolveResponse = {
      injected_text: "<advice>",
      injected_facts_text: "<facts>",
      injected_obligations_text: "<obligations>",
      offered_learning_ids: ["l-1"],
      offered_claim_ids: ["c-1"],
      offered_obligation_ids: ["i-1"],
    };

    expect(empty.injected_obligations_text).toBeUndefined();
    expect(served.injected_obligations_text).toBe("<obligations>");
    expect((served.offered_obligation_ids as string[])[0]).toBe("i-1");
  });

  test("a reinforce answer and the run status both carry the closure results", () => {
    // Excess-property checks make a regeneration that lost the field fail to compile.
    const closures: ObligationClosureResult[] = [
      { id: "o-1", disposition: "applied", status: "kept" },
      { id: "o-2", disposition: "busy", status: null },
    ];
    const accepted: BoundaryAcceptedResponse = {
      run_id: "support-agent:run-1",
      obligation_closures: closures,
    };
    const status: Pick<RunStatusResponse, "obligation_closures"> = {
      obligation_closures: closures,
    };

    expect((accepted.obligation_closures as ObligationClosureResult[])[1].disposition).toBe("busy");
    expect((status.obligation_closures as ObligationClosureResult[]).length).toBe(2);
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
      expect(body.agent_name).toBe("support-agent");
      expect(Object.keys(body).some((key) => /[A-Z]/.test(key))).toBe(false);
      expect(body.agentName).toBeUndefined();
      expect(body.agent_id).toBeUndefined();
    }
  });
});
