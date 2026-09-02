# ClaimSearchOut

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**as_of** | **object** | The world time the search reads the account at. |
**claims** | **object** | The same claims the text renders, one item per key. |
**computed_at** | **object** |  |
**cursor** | **object** | A filtered set&#x27;s next page cursor; null on the last page and on every other shape. | [optional]
**degraded** | **object** | Set when the result came from a narrower read than usual, saying why. | [optional]
**more_matched** | **object** | How many more claims the question&#x27;s words matched than the result hands over. | [optional]
**shape** | **object** |  |
**shares_no_word** | **object** | True when no claim shares a word with the question, so the claims are the nearest by meaning alone. | [optional]
**text** | **object** | The claims nearest the question, rendered by code under one line saying so; no model writes it. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

