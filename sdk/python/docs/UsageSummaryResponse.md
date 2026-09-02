# UsageSummaryResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_runs** | [**UsageRunAggregates**](UsageRunAggregates.md) |  |
**insights** | [**UsageInsightAggregates**](UsageInsightAggregates.md) |  | [optional]
**learnings** | [**UsageLearningAggregates**](UsageLearningAggregates.md) |  |
**period_end_exclusive** | **object** | Exclusive UTC boundary. |
**period_start** | **object** | Inclusive UTC boundary. |
**tenant_id** | **object** |  |
**test_agents** | [**UsageTestAgentAggregates**](UsageTestAgentAggregates.md) | The share of &#x60;agent_runs&#x60; that came from test agents. The totals stay whole, because that is what the tenant is billed on. | [optional]
**window** | [**UsageTimeWindow**](UsageTimeWindow.md) |  |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

