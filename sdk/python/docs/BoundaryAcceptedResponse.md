# BoundaryAcceptedResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**status** | **object** |  | [optional]
**run_id** | **object** | Echo of the caller-owned idempotency and correlation identifier; not a hosted run UUID. |
**is_duplicate** | **object** | True when this run was already done or already in flight, so nothing was dispatched. The request is still accepted, because at-least-once delivery makes a repeat legitimate, but no work follows. Callers that report success to a human must distinguish the two: reporting a no-op as delivered is what let a whole class of silently discarded distils go unnoticed. Absent on older servers, where it reads False. | [optional]
**worker_payload_version** | **object** | Compatibility version returned with the acceptance receipt. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

