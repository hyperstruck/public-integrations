# QuestionClaimReadResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_id** | **object** |  |
**as_of** | **object** | The snapshot this page was read against. Send it back with the cursor on every later page; a walk that does not is reading a moving target. |
**citations** | [**CitationsReport**](CitationsReport.md) |  |
**deterministic** | [**DeterministicArmReport**](DeterministicArmReport.md) |  |
**next_cursor** | **object** | The position to resume from, or null when the deterministic arm has no more rows. Null is a statement that the walk is finished, not an invitation to try again: a cursor is never issued for a page that would return nothing. | [optional]
**ordering** | [**PageOrdering**](PageOrdering.md) | Which ordering THIS page carries. It changes between the first page and the rest. |
**reach** | **object** | How far each of the question&#x27;s matched surfaces reached, one row per surface and match kind, so an over-broad match is visible in the response rather than only inferable from the rows. Read &#x60;entities_reached&#x60; for the magnitude, which is exact, and &#x60;entity_ids&#x60; for as much of the inventory as fits. | [optional]
**recall** | [**RecallArmReport**](RecallArmReport.md) |  |
**rows** | **object** |  |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

