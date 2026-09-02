# DocumentCitationRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**doc_id** | **object** | The customer&#x27;s own key for the document this passage lives in. Bounded in bytes to match the document store, and kept exactly as sent: two keys differing only by whitespace are two different documents. |
**end** | **object** | Character offset the span ends at. |
**segmenter_version** | **object** | Part of the pointer rather than metadata about it, because it is part of the unit&#x27;s identity: the same text segmented by a different version is different units. |
**start** | **object** | Character offset the span starts at. |
**text_sha256** | **object** | The normalised text version the span is an offset into. |
**unit_index** | **object** | Which unit of that text version. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

