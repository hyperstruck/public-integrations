# UsageLlmCallItem

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **object** |  | 
**model_id** | **object** |  | 
**component** | **object** |  | 
**provider** | **object** | Serving provider (e.g. groq, openai); null on older rows or the non-routed path. | [optional] 
**prompt_tokens** | **object** |  | 
**completion_tokens** | **object** |  | 
**total_tokens** | **object** |  | 
**cost_usd** | **object** | Raw provider cost for this call; null when not recorded. | [optional] 
**recorded_at** | **object** |  | 

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

