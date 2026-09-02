# ResolveRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_name** | **object** | Human-readable agent name, unique within your tenant. This is not the hosted agent UUID used in &#x60;/agents/{agent_id}&#x60; REST paths. If no agent with this name exists yet, a write-scoped call (&#x60;agents:write&#x60;) creates a minimal learning agent in your tenant. &#x60;POST /resolve&#x60; with only &#x60;agents:read&#x60; looks up an existing name and does not insert. Reuse the same name on resolve, observe, reinforce, and distill to target the same learning corpus. Clients conventionally namespace an agent-loop &#x60;run_id&#x60; as &#x60;&lt;agent_name&gt;:...&#x60;; if yours does, avoid the name &#x60;distill&#x60;, because &#x60;distill:&#x60; is reserved for corpus distillation run ids and every agent-loop write would be refused. |
**available_tools** | **object** |  | [optional]
**goal** | **object** | Goal about to be attempted by the external agent. |
**max_learnings** | **object** |  | [optional]
**model_context_window** | **object** |  | [optional]
**org_id** | **object** | Optional caller-owned organisation reference. | [optional]
**resolve_idempotency_key** | **object** | Opaque per-recall idempotency key, scoped to this run. Supply a value that is stable across retries of one recall and distinct across genuine recalls (a turn id, milestone id, or UUID) to recall more than once in a run: each distinct key accumulates its offers and is charged once; a retry with the same key neither double-charges nor double-records. Omit for a single recall per run (the default). | [optional]
**resolve_purpose** | [**ResolvePurpose**](ResolvePurpose.md) | Why this recall is being made. &#x60;agent_loop&#x60; covers executing agents and agent-owned integrations, attributing a non-empty response to reporting. &#x60;explicit_recall&#x60; is human-facing inspection and does not contribute to automated-loop value. | [optional]
**retrieval** | **object** | Retrieval depth. &#x60;fast&#x60; prioritises response time; &#x60;full&#x60; may return richer contextual relationships at higher latency. | [optional]
**run_id** | **object** | Caller-created correlation key. Reuse it with observe and reinforce; it does not reference a hosted &#x60;/runs/{run_id}&#x60; resource, and must not start with &#x60;distill:&#x60;, which is reserved for distillation jobs. |
**session_epoch** | **object** | An opaque token naming the window inside &#x60;session_id&#x60;. The host issues a new one when its context is compacted or cleared, which opens a new window in which everything may be offered again. Never a counter the server interprets. | [optional]
**session_id** | **object** | The host&#x27;s own session identifier, opaque to the server. Send it with &#x60;session_epoch&#x60; to stop a learning, standard or claim the same session window was already offered from being offered again. Omit it and every resolve behaves as it always did. | [optional]
**source_framework** | **object** | Producing host/framework (e.g. &#x27;mcp:cursor&#x27;), used to attribute the per-host funnel. Optional; backfilled from the episode at write-back. &#x60;unknown&#x60; is reserved: the loop-closure funnel groups runs with no attribution under that label and excludes them from alerting, so a value equal to it is normalised to unset rather than stored as a host. | [optional]
**standards_tools** | **object** | Every tool the host has used in this window. Standards that name tools are judged against these as well as &#x60;tool_in_play&#x60;, so one that was missed on a tool&#x27;s first call arrives on the next recall. Repeats are free: a standard already sent is not sent again. | [optional]
**tool_in_play** | **object** | The tool the host just ran for the first time in this window. The recall returns that tool&#x27;s standards only: no other learnings, no claims and no obligations. Omit it on every other recall. | [optional]
**undelivered_resolve_key** | **object** | With &#x60;undelivered_run_id&#x60;, the one resolve of that run that never reached the model, by its &#x60;resolve_idempotency_key&#x60; (&#x60;opening&#x60; for the keyless first one). Only that resolve&#x27;s offers leave the window and are released; omit it to withdraw the whole run. | [optional]
**undelivered_resolves** | **object** | Further resolves of this session that never reached the model, withdrawn as the one above is. | [optional]
**undelivered_run_id** | **object** | A run of this session whose recall was recorded as offered and then never reached the model. Its offers leave the window, so they are offered again, and are never credited. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

