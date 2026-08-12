# ResolveRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_name** | **object** | Human-readable agent name, unique within your tenant. This is not the hosted agent UUID used in &#x60;/agents/{agent_id}&#x60; REST paths. If no agent with this name exists yet, the platform creates one automatically on the first boundary call (a minimal learning agent scoped to your tenant). Reuse the same name on resolve, observe, reinforce, and distill to target the same learning corpus. Clients conventionally namespace an agent-loop &#x60;run_id&#x60; as &#x60;&lt;agent_name&gt;:...&#x60;; if yours does, avoid the name &#x60;distill&#x60;, because &#x60;distill:&#x60; is reserved for corpus distillation run ids and every agent-loop write would be refused. |
**org_id** | **object** | Optional caller-owned organisation reference. | [optional]
**run_id** | **object** | Caller-created correlation key. Reuse it with observe and reinforce; it does not reference a hosted &#x60;/runs/{run_id}&#x60; resource, and must not start with &#x60;distill:&#x60;, which is reserved for distillation jobs. |
**goal** | **object** | Goal about to be attempted by the external agent. |
**source_framework** | **object** | Producing host/framework (e.g. &#x27;mcp:cursor&#x27;), used to attribute the per-host funnel. Optional; backfilled from the episode at write-back. &#x60;unknown&#x60; is reserved: the loop-closure funnel groups runs with no attribution under that label and excludes them from alerting, so a value equal to it is normalised to unset rather than stored as a host. | [optional]
**available_tools** | **object** |  | [optional]
**max_learnings** | **object** |  | [optional]
**model_context_window** | **object** |  | [optional]
**retrieval** | **object** | Retrieval depth. &#x60;fast&#x60; prioritises response time; &#x60;full&#x60; may return richer contextual relationships at higher latency. | [optional]
**resolve_idempotency_key** | **object** | Opaque per-recall idempotency key, scoped to this run. Supply a value that is stable across retries of one recall and distinct across genuine recalls (a turn id, milestone id, or UUID) to recall more than once in a run: each distinct key accumulates its offers and is charged once; a retry with the same key neither double-charges nor double-records. Omit for a single recall per run (the default). | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

