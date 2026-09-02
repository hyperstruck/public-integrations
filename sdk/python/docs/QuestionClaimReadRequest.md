# QuestionClaimReadRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**as_of** | **object** | The snapshot this page reads against, as an instant. Omit on the first page and send back the &#x60;as_of&#x60; the response returned on every page after it. A value with no offset is read as UTC, which is also what comes back, so the walk is never pinned to a different instant than the one you meant. | [optional]
**cursor** | **object** | An opaque cursor from a previous page&#x27;s &#x60;next_cursor&#x60;. Null for the first page. It encodes a position rather than an offset, so a page is neither skipped nor repeated when rows are written underneath the walk. | [optional]
**include_superseded** | **object** | Include values that were replaced, in order along the chain, for a history question. Off by default because a superseded value WAS replaced and returning it as current is a lie. Note this is a different thing from a stale value, which nothing replaced and which is returned by default carrying &#x60;is_stale&#x60;. | [optional]
**page_size** | **object** | Rows per page. This bounds a page, never the answer: the deterministic arm is exhaustive and keyset-paged, so nothing is hidden past this number and it decides only how many round trips reading everything takes. | [optional]
**question** | **object** | The question to answer from this agent&#x27;s claims. Names in it are matched against the entities the agent has recorded, exactly and after normalisation only: there is no fuzzy matching here, and approximate matching is the recall arm&#x27;s job and is labelled as such. A question naming no recorded entity is a valid call that returns the recall arm alone. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

