# InsightEvidence

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_id** | **object** |  |
**changed_at** | **object** | When it changed, or the date it ended. | [optional]
**changed_by** | **object** | Who or which source changed it: a person&#x27;s name, or the source&#x27;s kind. | [optional]
**current_state** | [**InsightEvidenceItemState**](InsightEvidenceItemState.md) | &#x60;current&#x60;: the line still says what the finding read. &#x60;changed&#x60;: a different value now leads. &#x60;withdrawn&#x60;: a person said it isn&#x27;t so. &#x60;ended&#x60;: nothing stands on the line now. &#x60;conflicting&#x60;: two values wait on a decision. &#x60;unavailable&#x60;: the caller cannot see what would settle it. &#x60;unchecked&#x60;: the check could not run. &#x60;not_checked&#x60;: this kind of evidence is not checked yet. | [optional]
**current_text** | **object** | What stands on the line now, when the caller may see it. | [optional]
**kind** | **object** |  |
**quoted_ids** | **object** | Ids of the earlier or conflicting statements &#x60;text&#x60; also quotes. | [optional]
**read_text** | **object** | The value the finding read, as the line states it, when it differs from now. | [optional]
**ref_id** | **object** |  |
**text** | **object** |  |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

