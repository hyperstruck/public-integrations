# RunStatusResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**claim_count** | **object** | Claims written. Null until the job finishes, which is not zero. | [optional]
**corpus_items_lost** | **object** | Evidence items in a pass that failed, so they were never read. Non-zero means part of the corpus was not seen and resending is worthwhile; the claims from every other pass are still stored. | [optional]
**corpus_items_with_claims** | **object** | Evidence items that produced at least one claim. Null until the job finishes, and 0 on a job that carried no corpus. Read beside items_lost: a corpus that held few facts and one the extraction skipped are different answers, and only one is worth resending. | [optional]
**finished_at** | **object** |  | [optional]
**learning_count** | **object** | Learnings stored. Null until the job finishes, which is not zero. | [optional]
**run_id** | **object** |  |
**run_kind** | **object** |  |
**state** | [**RunState**](RunState.md) |  |
**zero_reason** | **object** | Why a count came back zero. Set only when one did. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

