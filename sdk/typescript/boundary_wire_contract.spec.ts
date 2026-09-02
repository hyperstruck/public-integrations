import {
  AgentsApiFetchParamCreator,
  ClaimItemOut,
  DeclineReason,
  DeclineRequest,
  DistillRequest,
  EpisodeModel,
  LearningBoundaryApiFetchParamCreator,
  ObserveRequest,
  ReinforceRequest,
  ResolvePurpose,
  ResolveRequest,
  ResolveResponse,
  RunDetailResponse,
  RunResponse,
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

  test("the recalled claims are Claim items, and every resolve response field stays optional", () => {
    // Optional in the generated type as well as in the schema: a consumer written against an
    // older server compiles unchanged. Excess-property checks make a regeneration that lost a
    // field, or kept the removed obligation block, fail to compile.
    const empty: ResolveResponse = {};
    const claim: ClaimItemOut = {
      id: "key-1",
      entity: { id: "e-1", name: "Harlow Freight", type: "company" },
      attribute: { id: "a-1", name: "fiscal year end", kind: "date", nature: "state", _protected: false },
      qualifiers: {},
      state: "settled",
    };
    const served: ResolveResponse = {
      injected_text: "<advice>",
      injected_facts_text: "<claims>",
      offered_learning_ids: ["l-1"],
      offered_claim_ids: ["key-1"],
      claims: [claim],
    };

    expect(empty.claims).toBeUndefined();
    expect((served.claims as ClaimItemOut[])[0].entity.name).toBe("Harlow Freight");
    expect((served.claims as ClaimItemOut[])[0].state).toBe("settled");
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

describe("AgentsApi argument positions", () => {
  // Query params are appended to the generated signature, never inserted, because callers
  // pass them positionally and every one is typed `any`, so a shift would compile silently.
  test("a listAgents call written before include_value existed still pages", () => {
    const fetchArgs = AgentsApiFetchParamCreator().listAgentsEndpointAgentsGet(
      undefined,
      undefined,
      undefined,
      undefined,
      undefined,
      undefined,
      undefined,
      undefined,
      25,
      "opaque-cursor",
      { headers: { "X-Trace": "test" } },
    );
    const query = new URL(fetchArgs.url, "https://example.test").searchParams;
    expect(query.get("limit")).toBe("25");
    expect(query.get("cursor")).toBe("opaque-cursor");
    expect(query.get("include_value")).toBe(null);
    expect(
      (fetchArgs.options.headers as Record<string, string>)["X-Trace"],
    ).toBe("test");
  });
});
