# AgentResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **object** |  | 
**name** | **object** |  | 
**description** | **object** |  | 
**status** | **object** |  | 
**model_provider** | [**ModelProvider**](ModelProvider.md) |  | 
**model_name** | **object** |  | 
**reasoning_profile** | [**ReasoningTier**](ReasoningTier.md) |  | 
**memory_profile** | **object** |  | 
**knowledge_scope** | **object** |  | 
**core_config** | [**AgentCoreConfigOutput**](AgentCoreConfigOutput.md) |  | 
**llm_credential** | **object** | Effective runtime LLM credential summary. Customer &#x60;agent_override&#x60; wins over &#x60;tenant_default&#x60;; if neither exists, platform fallback can identify the resolved provider/model with &#x60;credential_id&#x3D;null&#x60;. | [optional] 
**created_at** | **object** |  | 

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

