# ClaimItemOut

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**attribute** | [**AttributeRefOut**](AttributeRefOut.md) |  |
**beside** | **object** |  | [optional]
**conflict_kind** | **object** |  | [optional]
**conflicts_with** | **object** | For a conflict across two lines, the other line. | [optional]
**cosine** | **object** | On a search: the claim&#x27;s cosine to the question by meaning; null when the search by meaning did not run. | [optional]
**current** | **object** |  | [optional]
**entity** | [**EntityRefOut**](EntityRefOut.md) |  |
**history** | **object** |  | [optional]
**id** | **object** | The key: entity, attribute and qualifiers. |
**qualifiers** | **object** |  |
**reason_sentence** | **object** | For a conflicting item, why it waits for a decision, in the customer&#x27;s words. | [optional]
**series** | **object** |  | [optional]
**sources** | **object** | Each document and passage or step the item&#x27;s statements cite, once. | [optional]
**state** | **object** | settled, unanswered, conflicting, open, done or ended. |
**word_share** | **object** | On a search: the claim&#x27;s word weight for the question over the best in the result, 1 for the best and 0 when the question&#x27;s words did not reach it. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

