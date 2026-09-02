# ItemOutcomeModel

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**claims** | **object** | Claims written from this item. Null for now: the claim shelf counts its coverage per item internally and only the corpus-level totals cross the boundary, so a number here would be invented. Read corpus_items_with_claims and corpus_items_lost meanwhile. | [optional]
**is_compacted** | **object** | Whether the budget showed this item as a one-line summary rather than in full. Not a loss on its own: a compacted item still has its line in the run sketch every pass reads. | [optional]
**item_id** | **object** | The evidence item&#x27;s id, as you sent it. |
**learnings** | **object** | Learnings stored whose cited evidence was found in this item. |
**reason** | **object** | Why this item ended where it did. Set on an item that yielded nothing or was not read whole. | [optional]
**state** | **object** | read: every part of it reached a pass that returned. partially_read: some did, so silence about the rest is not evidence of absence. unread: none did. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

