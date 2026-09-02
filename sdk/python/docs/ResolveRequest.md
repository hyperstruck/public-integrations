# ResolveRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_name** | **object** | Human-readable agent name, unique within your tenant. This is not the hosted agent UUID used in &#x60;/agents/{agent_id}&#x60; REST paths. If no agent with this name exists yet, a write-scoped call (&#x60;agents:write&#x60;) creates a minimal learning agent in your tenant. &#x60;POST /resolve&#x60; with only &#x60;agents:read&#x60; looks up an existing name and does not insert. Reuse the same name on resolve, observe, reinforce, and distill to target the same learning corpus. Clients conventionally namespace an agent-loop &#x60;run_id&#x60; as &#x60;&lt;agent_name&gt;:...&#x60;; if yours does, avoid the name &#x60;distill&#x60;, because &#x60;distill:&#x60; is reserved for corpus distillation run ids and every agent-loop write would be refused. |
**as_of** | **object** | The moment the obligation block is computed against. Must carry an offset. Defaults to the server&#x27;s wall clock, which is what a live caller wants; supply it to reproduce a brief for a stated moment, or to render a batch of agents against one instant. | [optional]
**available_tools** | **object** |  | [optional]
**goal** | **object** | Goal about to be attempted by the external agent. |
**max_learnings** | **object** |  | [optional]
**max_obligations** | **object** | How many obligations the block may carry. Defaults to the shelf&#x27;s own cap. &#x60;0&#x60; turns the block off for this call. | [optional]
**model_context_window** | **object** |  | [optional]
**obligation_horizon_days** | **object** | How far ahead the obligation block looks, in days. Omitted, it follows &#x60;resolve_purpose&#x60;: &#x60;0&#x60; for &#x60;agent_loop&#x60; and &#x60;7&#x60; for &#x60;explicit_recall&#x60; (a human planning the week). The horizon governs obligations whose actionability window has not opened yet: one already inside its window is returned whatever the horizon, so &#x60;0&#x60; means overdue, due today, and anything already actionable, not overdue and due today alone. | [optional]
**org_id** | **object** | Optional caller-owned organisation reference. | [optional]
**resolve_idempotency_key** | **object** | Opaque per-recall idempotency key, scoped to this run. Supply a value that is stable across retries of one recall and distinct across genuine recalls (a turn id, milestone id, or UUID) to recall more than once in a run: each distinct key accumulates its offers and is charged once; a retry with the same key neither double-charges nor double-records. Omit for a single recall per run (the default). | [optional]
**resolve_purpose** | [**ResolvePurpose**](ResolvePurpose.md) | Why this recall is being made. &#x60;agent_loop&#x60; covers executing agents and agent-owned integrations, attributing a non-empty response to reporting. &#x60;explicit_recall&#x60; is human-facing inspection and does not contribute to automated-loop value. | [optional]
**retrieval** | **object** | Retrieval depth. &#x60;fast&#x60; prioritises response time; &#x60;full&#x60; may return richer contextual relationships at higher latency. | [optional]
**run_id** | **object** | Caller-created correlation key. Reuse it with observe and reinforce; it does not reference a hosted &#x60;/runs/{run_id}&#x60; resource, and must not start with &#x60;distill:&#x60;, which is reserved for distillation jobs. |
**source_framework** | **object** | Producing host/framework (e.g. &#x27;mcp:cursor&#x27;), used to attribute the per-host funnel. Optional; backfilled from the episode at write-back. &#x60;unknown&#x60; is reserved: the loop-closure funnel groups runs with no attribution under that label and excludes them from alerting, so a value equal to it is normalised to unset rather than stored as a host. | [optional]
**timezone** | **object** | IANA zone the obligation block&#x27;s dates are rendered in (for example &#x60;Australia/Sydney&#x60;). Resolved in order: this field, then the agent&#x27;s own &#x60;timezone&#x60;, then UTC with a marker on the block saying so. A date-only due is overdue only after end of day in the resolved zone, so this changes which obligations are late, not merely how they read. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

