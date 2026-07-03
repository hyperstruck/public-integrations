# ResolveRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_id** | **object** | The customer&#x27;s agent identifier (a string). | 
**org_id** | **object** |  | [optional] 
**run_id** | **object** |  | 
**goal** | **object** |  | 
**source_framework** | **object** | Producing host/framework (e.g. &#x27;mcp:cursor&#x27;), used to attribute the per-host funnel. Optional; backfilled from the episode at write-back. | [optional] 
**available_tools** | **object** |  | [optional] 
**max_learnings** | **object** |  | [optional] 
**model_context_window** | **object** |  | [optional] 
**retrieval** | **object** | Retrieval depth. &#x27;fast&#x27; (default): one ranked vector search, no graph. &#x27;full&#x27;: graph-enriched, heavier but richer. | [optional] 

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

