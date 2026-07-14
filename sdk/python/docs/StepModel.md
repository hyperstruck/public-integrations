# StepModel

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **object** | Step identifier unique within this episode. |
**name** | **object** | Tool or action name executed by the external agent. |
**args** | **object** | Arguments supplied to the tool or action. | [optional]
**status** | **object** | Whether this step completed or failed. | [optional]
**result** | **object** | Caller-supplied step result. Pre-redact secrets and personal data. | [optional]
**error** | **object** | Human-readable failure detail when &#x60;status&#x60; is &#x60;failed&#x60;. | [optional]
**declared_sensitivity** | **object** | Optional caller-declared sensitivity metadata for step fields. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

