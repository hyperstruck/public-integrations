# TextWindowUnit

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**end_char** | **object** | Where the returned &#x60;text&#x60; ends, in the coordinates of the returned text. A citation&#x27;s own offsets keep the stored text&#x27;s coordinates; see &#x60;source_end_char&#x60; and &#x60;withheld&#x60;. |
**heading_path** | **object** |  | [optional]
**is_truncated** | **object** | The stored text stops before &#x60;end_char&#x60;; the rest of this unit is no longer held. |
**source_end_char** | **object** | Where the stored unit ends, in the stored text&#x27;s coordinates, which citation pointers use. Set only when a protected value was withheld from &#x60;text&#x60;. | [optional]
**speaker** | **object** |  | [optional]
**start_char** | **object** |  |
**text** | **object** |  |
**unit_index** | **object** |  |
**withheld** | **object** | Each protected value withheld from &#x60;text&#x60;, so a citation span in stored coordinates can be moved onto the returned text. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

