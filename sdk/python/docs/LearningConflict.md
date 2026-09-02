# LearningConflict

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**conflict_type** | [**LearningConflictType**](LearningConflictType.md) | How the two learnings were adjudicated to disagree. Always &#x60;&#x60;contradiction&#x60;&#x60; today, which is the same relation the learning graph endpoint names &#x60;&#x60;CONTRADICTS&#x60;&#x60;; the other values are published so a later kind is additive rather than breaking. |
**learning_id_a** | **object** | One side of the disagreement. |
**learning_id_b** | **object** | The other side. The pair is unordered: a contradiction is mutual. Either side may be absent from &#x60;&#x60;items&#x60;&#x60;, because it fell outside the page or below &#x60;&#x60;min_utility&#x60;&#x60;; fetch it with GET /agents/{agent_id}/learnings/{learning_id}. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

