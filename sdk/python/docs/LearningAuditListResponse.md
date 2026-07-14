# LearningAuditListResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**items** | **object** |  |
**next_cursor** | **object** | Opaque cursor for the next page; null when exhausted. | [optional]
**facets** | **object** | Corpus-wide bucket counts; only populated on the first page. | [optional]
**omitted_learning_count** | **object** | Unreadable learnings omitted while building this page. This count is authoritative even if partial_failures are aggregated or truncated. | [optional]
**partial_failures** | **object** |  | [optional]
**retrieved_at** | **object** |  |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

