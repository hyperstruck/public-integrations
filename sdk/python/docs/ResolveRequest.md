# ResolveRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_id** | **object** | Caller-defined agent identifier. This is a string, not the hosted agent UUID used in &#x60;/agents/{agent_id}&#x60; paths. |
**org_id** | **object** | Optional caller-owned organisation reference. | [optional]
**run_id** | **object** | Caller-created correlation key. Reuse it with observe and reinforce; it does not reference a hosted &#x60;/runs/{run_id}&#x60; resource. |
**goal** | **object** | Goal about to be attempted by the external agent. |
**source_framework** | **object** | Producing host/framework (e.g. &#x27;mcp:cursor&#x27;), used to attribute the per-host funnel. Optional; backfilled from the episode at write-back. | [optional]
**available_tools** | **object** |  | [optional]
**max_learnings** | **object** |  | [optional]
**model_context_window** | **object** |  | [optional]
**retrieval** | **object** | Retrieval depth. &#x60;fast&#x60; prioritises response time; &#x60;full&#x60; may return richer contextual relationships at higher latency. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

