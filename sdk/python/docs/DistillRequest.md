# DistillRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_name** | **object** | Human-readable agent name, unique within your tenant. Not the hosted agent UUID used in `/agents/{agent_id}` REST paths. If no agent with this name exists yet, the platform creates one automatically on the first boundary call. Reuse the same name to target the same learning corpus. |
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

