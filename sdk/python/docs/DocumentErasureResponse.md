# DocumentErasureResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**cancelled_jobs** | **object** | Queued or running ingests for this document that the erasure cancelled. A deletion request is the one operation that must never queue behind other work. | [optional]
**completed_at** | **object** | When this erasure finished. Null while another request is still running it. | [optional]
**doc_id** | **object** |  |
**erasure_id** | **object** | This erasure&#x27;s own id. A note erased, sent again and erased again is two erasures with two ids; a repeated request for the same erasure names the same one. | [optional]
**is_complete** | **object** | True only when every scope reported a real count. A receipt that cannot say what it reached says so rather than reporting zero. |
**scopes** | **object** |  |
**versions** | **object** |  |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

