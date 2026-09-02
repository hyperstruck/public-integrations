# AnswerObligations

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**is_as_of_pinned** | **object** | Whether this half was read at the same instant as the claims. False today: the obligations listing takes no snapshot parameter, so it is read at the time of the call while the claims are read at the answer&#x27;s &#x60;as_of&#x60;. On an ordinary first-page call those are the same moment. On a call naming a past &#x60;as_of&#x60;, or on any later page echoing the first page&#x27;s, they are not, and this field says so rather than letting one &#x60;as_of&#x60; imply a consistent read across both halves. | [optional]
**is_available** | **object** |  | [optional]
**is_truncated** | **object** | True when this agent holds more obligations than the answer lists. Every other bound in this object discloses itself and so does this one: a list cut without saying so reads as the whole of what is owed. | [optional]
**items** | **object** |  | [optional]
**unavailable_reason** | **object** |  | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

