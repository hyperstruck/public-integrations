# DocumentSubmissionResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**doc_id** | **object** |  |
**enqueued** | **object** | False when identical bytes were already at head. The response is then a 200 rather than a 202, because a 202 on a duplicate promises work that will not happen and a client retrying on a timeout would believe it. |
**job_id** | **object** |  | [optional]
**state** | **object** | &#x60;queued&#x60; when this submission was enqueued, or the existing version&#x27;s state when identical bytes were already stored. |
**version** | **object** |  |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

