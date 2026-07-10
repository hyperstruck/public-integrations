# GoalRunRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**goal** | **object** | Goal or task for the hosted agent to execute. | 
**context** | **object** | Optional additional context passed to the reasoning runtime. | [optional] 
**session_id** | **object** | Optional session to associate with this run. | [optional] 
**worker_profile** | **object** | Logical worker profile (&#x60;default&#x60; or &#x60;large&#x60;). | [optional] 
**metadata** | **object** | Optional caller-defined metadata persisted onto the run row. | [optional] 
**sources** | **object** | Typed source-of-truth blocks (a transcript, a record set). The only request text the grounding gate admits as evidence; declaring any also activates the read-only faithfulness check so example text cannot be laundered into a claim. | [optional] 
**references** | **object** | Exemplar/calibration material shown to the model but never admitted as evidence. | [optional] 

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

