# AgentCreateRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **object** |  | 
**description** | **object** | Optional short agent description. | [optional] 
**status** | **object** | Hosted lifecycle flag (e.g. active, paused). | [optional] 
**model_provider** | [**ModelProvider**](ModelProvider.md) | Model provider for this agent. Defaults to the platform fallback provider (&#x60;openai&#x60;). | [optional] 
**model_name** | **object** | Provider-specific model id (maps to &#x60;AgentConfig.model&#x60;). Defaults to the platform fallback model. | [optional] 
**reasoning_profile** | [**ReasoningTier**](ReasoningTier.md) | Hosted reasoning tier applied to runs dispatched for this agent. | [optional] 
**memory_profile** | **object** | Platform memory integration preset (e.g. default, rich). | [optional] 
**knowledge_scope** | **object** | Knowledge isolation label stored on the agent row for the runtime. | [optional] 
**home_space_id** | **object** | Optional home space (&#x60;public.spaces&#x60;) for this agent. The composite FK &#x60;(tenant_id, home_space_id)&#x60; pins it to the caller&#x27;s tenant. | [optional] 
**core_config** | [**AgentCoreConfigInput**](AgentCoreConfigInput.md) | hyperstruck-core-aligned configuration blob. Required on create so every agent has explicit instructions. | 

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

