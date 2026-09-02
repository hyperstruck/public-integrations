# StepModel

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**args** | **object** | Arguments supplied to the tool or action. | [optional]
**declared_sensitivity** | **object** | Optional caller-declared metadata for this step. Sections whose value is a mapping carry per-field declarations (&#x60;args&#x60;, &#x60;result&#x60;, &#x60;result_attributes&#x60;, &#x60;result_integrity&#x60;, and the &#x60;provenance&#x60; record). Sections whose value is a string carry a single declaration, of which &#x60;subject&#x60; is the one the runtime reads: the argument key naming the entity this step&#x27;s result is about. | [optional]
**error** | **object** | Human-readable failure detail when &#x60;status&#x60; is &#x60;failed&#x60;. | [optional]
**id** | **object** | Step identifier unique within this episode. |
**is_refused** | **object** | The runtime decided this act must not happen. Valid only with &#x60;status&#x60; of &#x60;skipped&#x60; and no &#x60;error&#x60;: a step that ran and failed into a skip carries an error and is a run that tried, not one that held off. This is the signal restraint learning reads, and a &#x60;skipped&#x60; step without it reports an act that was never scheduled. | [optional]
**name** | **object** | Tool or action name executed by the external agent. |
**result** | **object** | Caller-supplied step result. Pre-redact secrets and personal data. | [optional]
**status** | **object** | Terminal status of this step. &#x60;skipped&#x60; covers every way a step did not run; on its own it does NOT mean the runtime refused the act. Pair it with &#x60;is_refused&#x60; to report a refusal. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

