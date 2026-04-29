# ResumeRunRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**suspension_id** | **object** | ID of the suspension to respond to (from the suspended run metadata). | 
**decision_type** | [**DecisionType**](DecisionType.md) | Decision type: approve, reject, modify, skip, provide_input, or partial_approve. | 
**data** | **object** | Optional decision payload (e.g. modified plan or tool args). Interpreted by hyperstruck-core per &#x60;&#x60;decision_type&#x60;&#x60; (e.g. &#x60;&#x60;provide_input&#x60;&#x60; merges into scratchpad metadata). | [optional] 
**decided_by** | **object** | Optional identifier of the human who made the decision. | [optional] 
**reason** | **object** | Optional human-readable reason (audit / trace; SDK-dependent visibility to the model). | [optional] 
**worker_profile** | **object** | Worker profile for the resume execution. | [optional] 
**metadata** | **object** | Optional caller-defined metadata for the child run. | [optional] 

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

