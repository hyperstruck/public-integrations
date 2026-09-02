# HarnessRepairPlan

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_id** | **object** |  |
**erasable** | **object** |  | [optional]
**etag** | **object** |  |
**is_truncated** | **object** | Whether the registry held more than this response reports. The overflow is counted rather than paged: an erased entity leaves the registry, so applying and re-planning converges. &#x60;etag&#x60; covers only what is listed here. | [optional]
**listed_claim_ids** | **object** | The harness-shaped claims on those mixed entities, left in place. | [optional]
**max_entities_per_apply** | **object** | How many of these one apply accepts. Published so a client batches by reading rather than by carrying its own copy of the number: a second copy is a constant that drifts silently, and the apply refuses an oversized approval rather than truncating it. | [optional]
**mixed** | **object** | Entities holding real claims beside harness-shaped ones. Listed and never erased: the claim store has no reversible retirement for a single claim, so retiring these is a schema change rather than a cascade. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

