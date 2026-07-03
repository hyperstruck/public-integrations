# BillingSummaryResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**plan_code** | **object** | Tenant plan code from the authenticated principal. | [optional] 
**window_kind** | [**BillingWindowKind**](BillingWindowKind.md) |  | 
**period_start** | **object** | Inclusive UTC billing window start. | 
**period_end_exclusive** | **object** | Exclusive UTC billing window end. | 
**hard_limit_usd** | **object** | Configured hard spend cap; null when unlimited. | [optional] 
**soft_limit_usd** | **object** | Configured soft spend cap; null when unset or unlimited. | [optional] 
**current_spend_usd** | **object** | Terminal billed spend in the window (runs + used learning holds). | 
**active_reservations_usd** | **object** | In-flight spend reservations for the current billing window. | 
**committed_usd** | **object** | current_spend_usd + active_reservations_usd. | 
**available_usd** | **object** | hard_limit_usd - committed_usd; null when unlimited. | [optional] 
**percent_used** | **object** | committed_usd / hard_limit_usd as a percentage; null when unlimited. | [optional] 
**status** | [**BillingSummaryStatus**](BillingSummaryStatus.md) |  | 

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

