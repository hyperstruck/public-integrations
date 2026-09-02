# RecallArmReport

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**guarantee** | [**ReadGuarantee**](ReadGuarantee.md) |  |
**limit** | **object** | The ceiling this arm was run under. Reaching it costs breadth and never costs a guarantee. |
**returned** | **object** | How many rows this arm actually contributed. |
**unavailable_reason** | **object** | Why the arm returned nothing, in plain words. It goes unavailable rather than failing the call, because the arm carrying the guarantee does not depend on it. Also set past the first page, where the arm does not extend at all. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

