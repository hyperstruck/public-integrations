# ObligationSourceCreditResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**applied** | **object** | Recency-discounted mass of outcomes that said the obligation was real. |
**last_update** | **object** |  |
**misled** | **object** | Recency-discounted mass of outcomes that said it was not: a drop for &#x27;not_an_obligation&#x27;, or an expiry for neglect. The other drop reasons and every other expiry reason move neither mass. |
**score** | **object** | The Wilson lower bound over those masses, blended with this agent&#x27;s pooled rate as an empirical-Bayes prior, so a source with three outcomes is read against what this agent&#x27;s sources do in general rather than judged on three outcomes. Advisory: nothing in the harvest lane reads it back to gate anything. |
**source_id** | **object** |  |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

