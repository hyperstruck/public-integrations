# StoredAnswerSummary

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**answer_id** | **object** |  |
**answer_unavailable_reason** | **object** | Why the answer was withheld. A reason this deployment does not know is given as its stored text. | [optional]
**as_of** | **object** |  | [optional]
**created_at** | **object** |  |
**expires_at** | **object** |  |
**findings** | [**StoredAnswerFindingCounts**](StoredAnswerFindingCounts.md) |  |
**question** | **object** | Null only for an answer stored in a shape that no longer carries a question. | [optional]
**url** | **object** | Where this answer is served at &#x60;detail&#x3D;everything&#x60;. Follow it rather than building the path. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

