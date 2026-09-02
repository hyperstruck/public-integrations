# BoundaryAcceptedResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**is_duplicate** | **object** | True when this run was already done or already in flight, so nothing was dispatched. The request is still accepted, because at-least-once delivery makes a repeat legitimate, but no work follows. Callers that report success to a human must distinguish the two: reporting a no-op as delivered is what let a whole class of silently discarded distils go unnoticed. Absent on older servers, where it reads False. | [optional]
**keys_awaiting_review** | **object** | How many of this agent&#x27;s keys have a changed value held for a person to review, because no person has said a wrong value there is harmless. The agent keeps the previous value, flagged pending, until someone reviews them. Null when it could not be read, and absent on older servers. | [optional]
**run_id** | **object** | Echo of the caller-owned idempotency and correlation identifier; not a hosted run UUID. |
**status** | **object** |  | [optional]
**value_error** | **object** | Why the value was not recorded, as a value error code such as &#x60;unknown_unit&#x60;. | [optional]
**value_event_id** | **object** | The value entry recorded or replayed, when there is one. | [optional]
**value_status** | **object** | What happened to the reinforce &#x60;value&#x60;: &#x60;recorded&#x60;, &#x60;replayed&#x60; (this key already recorded it), &#x60;tracking_disabled&#x60; (the agent does not track value), &#x60;rejected&#x60; (see &#x60;value_error&#x60;) or &#x60;failed&#x60; (try recording it again with POST /agents/{agent_id}/value-events). Null when no value was sent. | [optional]
**worker_payload_version** | **object** | Compatibility version returned with the acceptance receipt. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

