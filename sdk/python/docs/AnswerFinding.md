# AnswerFinding

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**citations** | **object** | Where in which version of the note those words are. | [optional]
**claim_ids** | **object** |  | [optional]
**cut_text** | **object** | This finding&#x27;s text with the checker&#x27;s flagged clause removed, kept beside the untouched &#x60;text&#x60; so nothing disappears unseen. Set only when the checker cut a clause. | [optional]
**document_ref** | **object** |  |
**finding_id** | **object** | The id this answer&#x27;s bullets cite this finding by. Unique within this response and meaningless outside it. Empty only from a deployment that predates publishing it. | [optional]
**kind** | [**FindingKind**](FindingKind.md) |  |
**quote** | **object** | The words in the note this finding rests on, when the read located them. | [optional]
**rests_on_held** | **object** | True when a unit this finding cites is covered by a dispute or identity hold, so what it says there is not yet confirmed. | [optional]
**superseded_by** | **object** | The &#x60;finding_id&#x60; of the later finding that moved this one on, when the supersession stage accepted it. Null when nothing superseded it, and on an answer stored before the stage existed. | [optional]
**support** | [**BulletSupport**](BulletSupport.md) | Whether the finding checker found this finding carried by what it cites. UNCHECKED on an answer stored before the checker existed, or when the checker did not return. | [optional]
**text** | **object** |  |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

