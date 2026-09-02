# InsightRefineResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**feasibility** | [**InsightFeasibility**](InsightFeasibility.md) | Whether the selected agents likely hold the data, judged only from their names and descriptions, not their contents. |
**missing_data** | **object** | Signals the agents may not have. | [optional]
**objective** | **object** | The draft rewritten as a specific, actionable insight. |
**warning** | **object** | Set unless feasibility is &#x60;likely&#x60;: what may be missing. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

