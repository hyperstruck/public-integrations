# ResolveFactLane

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**bound_entity_count** | **object** | How many entities the bind matched, before the trust floor and the lane&#x27;s token budget. Read against &#x60;offered_claim_ids&#x60; it separates a bind that found nothing from a render that refused everything it found. | [optional]
**is_complete** | **object** | Whether the facts returned are the whole of what the agent holds for this goal. False on any outcome that abandoned work, so a caller measuring grounding knows not to use this response as the denominator. |
**is_degraded** | **object** | Whether the lane failed to run, as opposed to running and finding nothing. True is an operational problem on our side, not a fact about the caller&#x27;s corpus. |
**outcome** | **object** | Why the lane is what it is: bound, bound_partial, no_match, goal_truncated, budget_exhausted, failed, suppressed, or binder_absent. &#x27;no_match&#x27; is the only one meaning the agent genuinely holds nothing for this goal. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

