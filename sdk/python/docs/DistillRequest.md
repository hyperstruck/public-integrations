# DistillRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_id** | **object** | Caller-defined agent identifier. This is a string, not the hosted agent UUID used in &#x60;/agents/{agent_id}&#x60; paths. |
**org_id** | **object** | Optional caller-owned organisation reference. | [optional]
**run_id** | **object** | Caller-created idempotency and tracing identifier. It must start with &#x60;distill:&#x60; and does not reference a hosted run. |
**goal** | **object** | The extraction intent. |
**evidence** | **object** |  | [optional]
**outcome** | [**DistillOutcomeModel**](DistillOutcomeModel.md) |  |
**evaluation** | **object** | Reviewer verdict or contrast aid; folded into the grounding corpus. | [optional]
**synthesis_notes** | **object** |  | [optional]
**source_framework** | **object** |  | [optional]
**occurred_at** | **object** |  | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

