# StepModel

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**args** | **object** | Arguments supplied to the tool or action. | [optional]
**declared_sensitivity** | **object** | Optional caller-declared metadata for this step. Sections whose value is a mapping carry per-field declarations (&#x60;args&#x60;, &#x60;result&#x60;, &#x60;result_attributes&#x60;, &#x60;result_integrity&#x60;, and the &#x60;provenance&#x60; record). Sections whose value is a string carry a single declaration, of which &#x60;subject&#x60; is the one the runtime reads: the argument key naming the entity this step&#x27;s result is about. A provenance member (&#x60;source_id&#x60;, &#x60;channel&#x60;, &#x60;genre&#x60;, &#x60;author&#x60;, &#x60;source_time&#x60;, &#x60;source_class&#x60;) declared at the top level instead of nested under &#x60;provenance&#x60; is refused, because a flat one is read as no declaration at all rather than as a second home for the same fact. The &#x60;provenance&#x60; record may also carry a citation into a stored document: &#x60;doc_id&#x60;, &#x60;text_sha256&#x60; and &#x60;segmenter_version&#x60; as strings, and &#x60;unit_index&#x60;, &#x60;start&#x60; and &#x60;end&#x60; as INTEGERS. Those six travel together and name the exact passage this step&#x27;s evidence was drawn from, so a learning built from it can be resolved back to the text it rests on. The offsets must be integers: a numeric string is refused deliberately, because it is a second shape for the same pointer. &#x60;attacker_reachable&#x60; is a BOOLEAN: &#x60;true&#x60; says someone outside your organisation can write into this source, and holds what is read from it as untrusted. &#x60;false&#x60; is ignored, because a source vouching for itself is not believed, and any other shape is dropped. | [optional]
**error** | **object** | Human-readable failure detail when &#x60;status&#x60; is &#x60;failed&#x60;. | [optional]
**id** | **object** | Step identifier unique within this episode. |
**is_refused** | **object** | The runtime decided this act must not happen. Valid only with &#x60;status&#x60; of &#x60;skipped&#x60; and no &#x60;error&#x60;: a step that ran and failed into a skip carries an error and is a run that tried, not one that held off. This is the signal restraint learning reads, and a &#x60;skipped&#x60; step without it reports an act that was never scheduled. | [optional]
**name** | **object** | Tool or action name executed by the external agent. |
**result** | **object** | Caller-supplied step result. Pre-redact secrets and personal data. | [optional]
**status** | **object** | Terminal status of this step. &#x60;skipped&#x60; covers every way a step did not run; on its own it does NOT mean the runtime refused the act. Pair it with &#x60;is_refused&#x60; to report a refusal. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

