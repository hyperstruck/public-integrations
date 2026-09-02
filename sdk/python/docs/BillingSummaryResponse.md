# BillingSummaryResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**active_reservations_usd** | **object** | In-flight spend reservations for the current billing window. |
**available_usd** | **object** | hard_limit_usd - committed_usd; null when unlimited. | [optional]
**committed_usd** | **object** | current_spend_usd + active_reservations_usd. |
**current_spend_usd** | **object** | Spend billed in the period: finished runs, plus finished work at the real cost of its model calls, or at its estimate where the cost was not measured. |
**estimated_portion_usd** | **object** | The part of current_spend_usd counted at an estimate rather than a measured cost. It shrinks as billing periods roll. | [optional]
**hard_limit_usd** | **object** | Configured hard spend cap; null when unlimited. | [optional]
**percent_used** | **object** | committed_usd / hard_limit_usd as a percentage; null when unlimited. | [optional]
**period_end_exclusive** | **object** | Exclusive UTC end of the current billing period. |
**period_start** | **object** | Inclusive UTC start of the current billing period, computed from the subscription&#x27;s start date and length. |
**plan_code** | **object** | Tenant plan code from the authenticated principal. | [optional]
**soft_limit_usd** | **object** | Configured soft spend cap; null when unset or unlimited. | [optional]
**status** | [**BillingSummaryStatus**](BillingSummaryStatus.md) |  |
**window_kind** | [**BillingWindowKind**](BillingWindowKind.md) |  |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

