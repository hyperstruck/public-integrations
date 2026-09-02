# LearningInstanceEvidenceResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**author** | **object** |  | [optional]
**basis** | **object** | How the locator was obtained: observed (the client ran git) or reported (a caller supplied it). | [optional]
**citation** | **object** | The span of a stored document this evidence was drawn from, when it came through one. | [optional]
**created_at** | **object** |  |
**entity_values** | **object** |  |
**grounding_digest** | **object** |  | [optional]
**grounding_ref** | **object** |  | [optional]
**id** | **object** |  |
**is_situation_derived** | **object** | True when the situation was reconstructed by the repair of records whose cue held a source label, rather than supplied by whoever wrote the case. | [optional]
**locator** | **object** | Where in a repository this example was read, when the source is a coding session. | [optional]
**outcome** | **object** |  |
**outcome_label** | **object** | Whether this case demonstrated the rule succeeding or failing. | [optional]
**situation** | **object** |  | [optional]
**source_channel** | **object** |  | [optional]
**source_context** | **object** | Deprecated. Now the caller&#x27;s superseded single-facet provenance value, so it is null for every case written before provenance was recorded: it used to echo back the retrieval cue, which is now returned as &#x60;situation&#x60;. A label that was written into the cue by the old path is returned as &#x60;source_channel&#x60; once the record is repaired. | [optional]
**source_genre** | **object** |  | [optional]
**source_id** | **object** |  | [optional]
**source_kind** | **object** | What kind of origin this example names: coding_session, document, system_record, message, or unsourced. Derived from the record, never from who wrote it. | [optional]
**source_plan_id** | **object** |  | [optional]
**source_step_id** | **object** |  | [optional]
**source_time** | **object** |  | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

