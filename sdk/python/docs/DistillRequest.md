# DistillRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_name** | **object** | Human-readable agent name, unique within your tenant. This is not the hosted agent UUID used in &#x60;/agents/{agent_id}&#x60; REST paths. If no agent with this name exists yet, a write-scoped call (&#x60;agents:write&#x60;) creates a minimal learning agent in your tenant. &#x60;POST /resolve&#x60; with only &#x60;agents:read&#x60; looks up an existing name and does not insert. Reuse the same name on resolve, observe, reinforce, and distill to target the same learning corpus. Clients conventionally namespace an agent-loop &#x60;run_id&#x60; as &#x60;&lt;agent_name&gt;:...&#x60;; if yours does, avoid the name &#x60;distill&#x60;, because &#x60;distill:&#x60; is reserved for corpus distillation run ids and every agent-loop write would be refused. |
**evaluation** | **object** | Reviewer verdict or contrast aid; folded into the grounding corpus. | [optional]
**evidence** | **object** |  | [optional]
**goal** | **object** | The extraction intent. |
**max_learnings** | **object** | Maximum number of learnings to extract from this distill job. Defaults to 10; lower for sparse corpora or raise for large, dense documents. | [optional]
**occurred_at** | **object** | RFC 3339 time the corpus was produced. It stamps the learnings so they decay from the real time rather than from ingestion, and it anchors any obligation harvested from the corpus, so a relative deadline (&#x27;by Friday&#x27;, &#x27;end of next week&#x27;) resolves against the week the writer was in rather than the week we received it. Carry the offset: a date-only deadline belongs to a calendar day in the writer&#x27;s own zone, and a bare UTC timestamp reads it in ours. An item that declares its own &#x60;declared_sensitivity.provenance.source_time&#x60; uses that instead, for that item. | [optional]
**org_id** | **object** | Optional caller-owned organisation reference. | [optional]
**outcome** | [**DistillOutcomeModel**](DistillOutcomeModel.md) |  |
**run_id** | **object** | Caller-created idempotency and tracing identifier. It must start with &#x60;distill:&#x60; and does not reference a hosted run. |
**source_framework** | **object** |  | [optional]
**synthesis_notes** | **object** |  | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

