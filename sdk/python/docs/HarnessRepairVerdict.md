# HarnessRepairVerdict

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**canonical_name** | **object** |  |
**claim_count** | **object** |  |
**consent** | **object** | This entity&#x27;s own consent token, over everything the erasable test reads. Fold the tokens of the entities being approved into the If-Match on apply; the plan&#x27;s own &#x60;etag&#x60; is that fold over the whole erasable list, for approving all of it. |
**entity_id** | **object** |  |
**evidence** | **object** |  | [optional]
**harness_claim_count** | **object** |  |
**is_host_id** | **object** | Whether the entity&#x27;s own name has the shape of an id the host mints. Never enough to erase on its own: the same shape is a product code or a version string. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

