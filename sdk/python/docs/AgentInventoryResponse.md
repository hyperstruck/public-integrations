# AgentInventoryResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_limit** | **object** | How many agents the plan allows. Present when &#x60;include_summary&#x60; is true. | [optional]
**agents_used** | **object** | How many agents count against &#x60;agent_limit&#x60; now. | [optional]
**as_of** | **object** | Fixed window anchor used for metric sorts/summaries. | [optional]
**items** | **object** |  |
**next_cursor** | **object** | When set, another page exists: pass as &#x60;cursor&#x60;. | [optional]
**test_agent_count** | **object** | Every test agent in the caller&#x27;s readable spaces, whatever its reasoning profile and whatever the other filters. Present when &#x60;include_summary&#x60; is true. | [optional]
**test_agents_used** | **object** | How many of &#x60;agents_used&#x60; are test agents. Present when &#x60;include_summary&#x60; is true. | [optional]
**window** | [**UsageTimeWindow**](UsageTimeWindow.md) |  |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

