# ReadDocument

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**claims** | **object** |  | [optional]
**document_ref** | **object** |  |
**first_seen_at** | **object** |  | [optional]
**held_unit_indices** | **object** | Each unit of this note a dispute or identity hold covers, with the version it indexes. Findings citing one of them carry &#x60;rests_on_held&#x60;. | [optional]
**is_claims_on_earlier_version** | **object** | True when the note&#x27;s text was read at its current version but some of its claims were read from an earlier one, so a passage may differ from the text around it. | [optional]
**is_claims_truncated** | **object** |  | [optional]
**is_concern_linked** | **object** |  | [optional]
**is_over_budget** | **object** |  | [optional]
**is_scheduled** | **object** |  | [optional]
**read** | [**DocumentRead**](DocumentRead.md) |  |
**text_absence** | **object** |  | [optional]
**text_read** | [**DocumentTextRead**](DocumentTextRead.md) |  | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

