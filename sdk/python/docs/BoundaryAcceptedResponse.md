# BoundaryAcceptedResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**is_duplicate** | **object** | True when this run was already done or already in flight, so nothing was dispatched. The request is still accepted, because at-least-once delivery makes a repeat legitimate, but no work follows. Callers that report success to a human must distinguish the two: reporting a no-op as delivered is what let a whole class of silently discarded distils go unnoticed. Absent on older servers, where it reads False. | [optional]
**obligation_closures** | **object** | One result per obligation outcome the request carried, in the order they were sent. Null when the request carried none, which is every call that reported nothing to close, and also what an older server returns. Closures are applied synchronously even though the learning work is not, so this is decided by the time you are answered: unlike the rest of this response it is a result, not an acknowledgement. | [optional]
**run_id** | **object** | Echo of the caller-owned idempotency and correlation identifier; not a hosted run UUID. |
**status** | **object** |  | [optional]
**worker_payload_version** | **object** | Compatibility version returned with the acceptance receipt. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

