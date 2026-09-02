# ObligationOrgListResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**is_space_filtered** | **object** | True when the caller&#x27;s readable-space set narrowed this page. A short page then means some rows sit outside your spaces, not that the tenant holds no more. False when the caller reads unrestricted. | [optional]
**items** | **object** |  |
**next_cursor** | **object** | Opaque page cursor. Pass it back verbatim as ?after&#x3D; to fetch the next page; its shape is internal and may change, so never parse or construct it. Null on the last page. | [optional]
**withheld_count** | **object** | How many rows of this page&#x27;s window your readable spaces hid from you: rows in a space you were not granted, and rows with no space at all, which the floor fail-closes on. Best effort over the page window, not a tenant-wide tally, and always 0 when is_space_filtered is false. It exists so a short page is explainable: the agent-scoped list is entitled per agent rather than per space and shows those rows, so without this the two surfaces silently disagree about how much there is. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

