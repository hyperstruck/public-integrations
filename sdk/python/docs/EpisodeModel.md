# EpisodeModel

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**run_id** | **object** | Caller-created correlation and idempotency identifier. It does not reference a hosted &#x60;/runs/{run_id}&#x60; resource. |
**goal** | **object** | Goal attempted by the external agent. |
**steps** | **object** | Ordered actions and results from the completed episode. | [optional]
**outcome** | [**OutcomeModel**](OutcomeModel.md) | Terminal outcome of the episode. |
**source_framework** | **object** | Optional external framework or host identifier. | [optional]
**thread_id** | **object** | Optional caller-owned conversation or thread identifier. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

