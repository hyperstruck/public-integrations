# InsightFindingResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**confidence** | **object** |  |
**created_at** | **object** |  |
**definition_id** | **object** |  |
**draft_held** | **object** | Why the draft is held back, when the evidence under it has changed, is waiting on a decision, or could not be checked; null otherwise. | [optional]
**draft_message** | **object** | The drafted message. Null while &#x60;draft_held&#x60; is set, unless the caller passed &#x60;include_held_drafts&#x3D;true&#x60;. | [optional]
**evidence** | **object** |  |
**evidence_state** | [**InsightEvidenceState**](InsightEvidenceState.md) | Whether the evidence under the finding still says what it read. Worked out on every read. | [optional]
**id** | **object** |  |
**priority** | [**InsightPriority**](InsightPriority.md) |  |
**recommended_action** | **object** |  | [optional]
**replaced_by** | **object** | The finding that replaced this one, when its status is &#x60;replaced&#x60;. | [optional]
**run_id** | **object** |  |
**status** | [**InsightFindingStatus**](InsightFindingStatus.md) |  |
**subject** | **object** |  | [optional]
**summary** | **object** |  |
**title** | **object** |  |
**updated_at** | **object** |  |
**why_now** | **object** |  | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

