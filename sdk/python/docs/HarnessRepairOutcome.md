# HarnessRepairOutcome

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_id** | **object** |  |
**deferred_over_bound** | **object** | Always empty now that the request itself is bounded at what one apply erases. Kept so a client written against the earlier shape still parses the response. | [optional]
**erased** | **object** |  | [optional]
**failures** | **object** | Entity id and cause for each cascade that did not run. | [optional]
**skipped_no_longer_erasable** | **object** | Approved entities that are no longer field dumps, or were never in the plan. An entity whose evidence CHANGED refuses the whole apply through the consent token instead, because it is the case the operator has to read again. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

