# LearningSearchResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**conflicts** | **object** | Recorded disagreements involving the learnings in &#x60;&#x60;items&#x60;&#x60;: an entry is kept when either side is in the page, so a contradiction survives its opponent being truncated away. Empty is not evidence of a clean corpus: the list is also empty when the graph holding these relations could not be read, and for org-scope search, which reads the shared pool and has no curated retrieval to surface them. | [optional]
**is_conflicts_truncated** | **object** | Whether &#x60;&#x60;conflicts&#x60;&#x60; was cut at its cap. The list is bounded by how many disagreements the corpus records among the retrieved candidates rather than by &#x60;&#x60;limit&#x60;&#x60;, so a dense cluster is capped rather than returned whole. | [optional]
**items** | **object** |  |
**total** | **object** | Number of results returned. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

