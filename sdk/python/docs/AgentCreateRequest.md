# AgentCreateRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **object** | Human-readable agent name, unique within the tenant. |
**description** | **object** | Optional short agent description. | [optional]
**status** | [**AgentStatus**](AgentStatus.md) | Hosted lifecycle state (active, paused, archived). | [optional]
**reasoning_profile** | [**ReasoningTier**](ReasoningTier.md) | Hosted reasoning tier applied to runs dispatched for this agent. | [optional]
**home_space_id** | **object** | Optional UUID of the accessible space that owns this agent. | [optional]
**core_config** | [**AgentCoreConfig**](AgentCoreConfig.md) | Runtime instructions and optional execution settings. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

