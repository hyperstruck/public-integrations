# ResumeRunRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**data** | **object** | Optional decision payload, such as modified instructions, selected items, or additional human input. | [optional]
**decision_type** | [**DecisionType**](DecisionType.md) | Decision type: approve, reject, modify, skip, provide_input, or partial_approve. |
**metadata** | **object** | Optional caller-defined metadata for the child run. | [optional]
**reason** | **object** | Optional human-readable reason (audit / trace; SDK-dependent visibility to the model). | [optional]
**suspension_id** | **object** | ID of the suspension to respond to (from the suspended run metadata). |
**worker_profile** | **object** | Worker profile for the resume execution. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

