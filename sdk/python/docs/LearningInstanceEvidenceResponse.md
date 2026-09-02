# LearningInstanceEvidenceResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**author** | **object** |  | [optional]
**created_at** | **object** |  |
**entity_values** | **object** |  |
**id** | **object** |  |
**is_situation_derived** | **object** | True when the situation was reconstructed by the repair of records whose cue held a source label, rather than supplied by whoever wrote the case. | [optional]
**outcome** | **object** |  |
**situation** | **object** |  | [optional]
**source_channel** | **object** |  | [optional]
**source_context** | **object** | Deprecated. Now the caller&#x27;s superseded single-facet provenance value, so it is null for every case written before provenance was recorded: it used to echo back the retrieval cue, which is now returned as &#x60;situation&#x60;. A label that was written into the cue by the old path is returned as &#x60;source_channel&#x60; once the record is repaired. | [optional]
**source_genre** | **object** |  | [optional]
**source_id** | **object** |  | [optional]
**source_time** | **object** |  | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

