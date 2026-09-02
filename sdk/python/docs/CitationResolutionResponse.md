# CitationResolutionResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**citation** | [**CitationModel**](CitationModel.md) |  |
**digest** | **object** |  | [optional]
**doc_id** | **object** | The erased document, on &#x60;erased&#x60;. | [optional]
**outcome** | **object** |  |
**quote** | **object** | The passage, on &#x60;resolved&#x60;. | [optional]
**reason** | **object** | Why nothing resolved, on &#x60;missing&#x60;. | [optional]
**retained_end_char** | **object** |  | [optional]
**retained_quote** | **object** | What survives on &#x60;truncated&#x60;: the stored excerpt is bounded, so a span beyond it returns the part that is still held rather than a silent shortening. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

