# AnswerObligation

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**due_at** | **object** | The first instant this is overdue, in UTC. Under &#x60;date&#x60; precision that is the start of the day after &#x60;due_local&#x60; in &#x60;due_tz&#x60;, a day later than the day itself: render &#x60;due_local&#x60; rather than this, or your answer and the obligations surface will state different dates for one commitment. | [optional]
**due_local** | **object** | The due date as a reader should see it: the day itself, in &#x60;due_tz&#x60;, under &#x60;date&#x60; precision, and the instant under &#x60;datetime&#x60; precision, in the agent&#x27;s default zone (UTC when it has none). Present whenever &#x60;due_at&#x60; is. Render this, not &#x60;due_at&#x60;. | [optional]
**due_precision** | **object** | &#x60;date&#x60; when a day was meant and &#x60;datetime&#x60; when an instant was. Null when there is no due date. | [optional]
**due_tz** | **object** | The zone the due was stated in: an IANA zone or, when that is all the source gave, a fixed offset. Null when no due date was set. | [optional]
**due_tz_basis** | **object** | Where &#x60;due_tz&#x60; came from: &#x60;phrase&#x60;, &#x60;note&#x60;, &#x60;agent&#x60;, &#x60;offset&#x60;, &#x60;caller&#x60;, or &#x60;defaulted&#x60; when nothing named a zone and UTC was assumed, so the day may be wrong. Null when unknown. | [optional]
**entity_id** | **object** |  | [optional]
**entity_name** | **object** |  | [optional]
**is_terminal** | **object** |  |
**obligation_id** | **object** |  |
**premise_claim_ids** | **object** | The claims this obligation was derived from, which is how it is placed under a document. | [optional]
**statement** | **object** |  |
**status** | **object** |  |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

