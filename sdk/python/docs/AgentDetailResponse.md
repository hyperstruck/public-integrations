# AgentDetailResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**access** | **object** | Present when &#x60;include_access&#x60; is true. | [optional]
**core_config** | [**AgentCoreConfig**](AgentCoreConfig.md) | What the agent runs with. An agent that was given no configuration carries the defaults here and &#x60;is_configured&#x60; false. |
**created_at** | **object** |  |
**description** | **object** |  | [optional]
**holdings** | **object** | Present when &#x60;include_summary&#x60; is true. | [optional]
**home_space_id** | **object** | Home space UUID for this agent, if any. | [optional]
**id** | **object** |  |
**is_configured** | **object** | False for an agent that was given no configuration, such as one created from a name alone. It can hold documents and answer from them, and cannot run a goal. |
**name** | **object** |  |
**reasoning_profile** | [**ReasoningTier**](ReasoningTier.md) |  |
**status** | **object** |  |
**summary** | **object** |  | [optional]
**test** | **object** | The test label, or null for an agent that is not a test agent. | [optional]
**updated_at** | **object** |  |
**value** | **object** | Lifetime value and how to record more. Present when &#x60;include_value&#x60; is true or the list is sorted by value. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

