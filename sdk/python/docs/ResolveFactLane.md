# ResolveFactLane

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**is_complete** | **object** | Whether the block holds everything the account holds for this goal. False on any outcome that cut or abandoned work, so a measurement does not use it as the denominator. |
**is_degraded** | **object** | Whether the lane could not run, as opposed to running and finding nothing. True is an operational state on our side, not a statement about the account. |
**outcome** | **object** | bound (the block holds the claims about the entities the goal names), bound_partial (the block&#x27;s budget cut some claims), no_match (the goal names an entity the account holds and the account holds no live claim about it), no_entity_named (the goal names no entity the account holds, so nothing was looked up; the account may still hold claims the goal describes, which an answer finds), suppressed (a tool&#x27;s first-use resolve carries no claims), not_replayed (the agent&#x27;s documents are still being replayed into the claim store) or failed (the recall could not run). &#x27;no_match&#x27; is the only one meaning the account holds nothing for this goal. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

