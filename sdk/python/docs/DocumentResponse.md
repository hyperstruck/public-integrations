# DocumentResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**doc_id** | **object** |  |
**extraction_reason** | **object** |  | [optional]
**extraction_state** | **object** | Whether the head version&#x27;s passages have been read into claims. &#x60;failed&#x60; carries &#x60;extraction_reason&#x60; and is retried daily; &#x60;not_eligible&#x60; means this agent&#x27;s claim extraction is off. Absent until a version is stored. | [optional]
**head_version** | **object** |  | [optional]
**ingest** | **object** | The queue&#x27;s view, read from the job row. Absent when nothing was ever enqueued for this document. | [optional]
**ingest_error** | **object** | Why the last job stopped, when &#x60;ingest&#x60; is &#x60;failed&#x60;. A job cancelled by an erasure reports here too, saying so. | [optional]
**version_state** | **object** | Core&#x27;s VersionState for the head version. Never conflated with &#x60;ingest&#x60;: &#x60;superseded&#x60; is citable by design and is not a failure. | [optional]
**versions** | **object** |  | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

