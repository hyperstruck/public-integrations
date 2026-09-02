# ValueEventCreate

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**amount_usd** | **object** | A dollar figure someone stated. Requires &#x60;baseline&#x60;. | [optional]
**baseline** | **object** | What the outcome would have cost without the agent, in words a reviewer can check, e.g. &#x60;Outside counsel quote: $50k, 3 business days&#x60;. Required with &#x60;amount_usd&#x60;. | [optional]
**category** | **object** |  | [optional]
**claim_ids** | **object** | Claims to credit. Requires a known &#x60;run_id&#x60;; each must be one that run was offered. | [optional]
**evidence_url** | **object** |  | [optional]
**idempotency_key** | **object** | Your key for this outcome, e.g. &#x60;placement:req-8812&#x60;. A retry with the same body returns the original entry; a different body under the same key is refused (409). Keys starting &#x60;reversal:&#x60; or &#x60;auto:&#x60; are reserved for the platform. |
**kind** | **object** | Leave unset (measured). Send &#x60;estimated&#x60; only to mark your own figure as a guess. | [optional]
**learning_ids** | **object** | Learnings to credit. With a known &#x60;run_id&#x60;, each must be one that run was offered; otherwise each must belong to this agent. | [optional]
**note** | **object** |  | [optional]
**occurred_at** | **object** | When the outcome happened, if not now. May be in the past, not the future. A time without an offset is read as UTC. | [optional]
**quantity** | **object** | How many units happened. Defaults to 1 when &#x60;unit_key&#x60; is set. | [optional]
**run_id** | **object** | The learning run that produced the outcome (the caller-owned &#x60;run_id&#x60; from resolve). Credits the learnings and claims that run was offered, including up to a year after it closed, as long as value tracking was on when it closed. | [optional]
**time_saved_minutes** | **object** | Minutes saved. Alone, dollars are derived at the profile&#x27;s hourly rate; beside &#x60;amount_usd&#x60;, it is recorded as extra context. | [optional]
**unit_key** | **object** | Rate-card unit that happened. Dollars come from the rate card, not from you. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

