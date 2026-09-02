# AnswerRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**as_of** | **object** | Answer as the shelf stood at this instant. Defaults to now; a future instant is clamped. | [optional]
**asker** | **object** | Who is asking. Conditions about whose a thing is are settled against this, and nothing infers it: an organisation is rarely named in its own documents. | [optional]
**budget_chars** | **object** | Characters of documents to read. Defaults to 400,000; raising it reads more history and costs more. | [optional]
**detail** | [**AnswerDetail**](AnswerDetail.md) | How much of the answer to return: &#x60;answer&#x60; (the default), &#x60;findings&#x60;, &#x60;claims&#x60; or &#x60;everything&#x60;, each the one before plus one addition. Any level is also served later from the answer&#x27;s &#x60;more&#x60; links, as the same answer rather than a new one. | [optional]
**question** | **object** |  |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

