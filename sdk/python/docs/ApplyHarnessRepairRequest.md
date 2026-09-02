# ApplyHarnessRepairRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**entity_ids** | **object** | Entity ids from the plan&#x27;s &#x60;erasable&#x60; list, each a UUID. Bounded at what one apply erases, so an oversized approval is refused rather than silently truncated: a truncated approval is consent to a set the operator never saw. Apply again after a fresh plan; an erased entity leaves the registry, so it converges. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

