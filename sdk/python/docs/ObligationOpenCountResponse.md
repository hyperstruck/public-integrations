# ObligationOpenCountResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**is_reconciled** | **object** | True when the two agree and false when the metered figure has drifted. Null when there is nothing to reconcile against: either the reconcile has not written for this day (metered_reconciled_at is null) or the caller is space-filtered and there is no tenant-wide live figure. An unwritten day is deliberately not reported as drift, because for most of every day that is the healthy state. | [optional]
**is_space_filtered** | **object** | True when the caller&#x27;s readable spaces are a subset of the tenant&#x27;s, so live_open_count covers only those spaces. The metered figure is tenant-wide and is withheld in that case, because the reconciliation it exists for is a tenant-level question and comparing a space-narrowed live count against a tenant-wide meter reports drift that is only the caller&#x27;s own visibility. | [optional]
**live_open_count** | **object** | Open obligations counted now. Across the tenant&#x27;s agents for a caller with org-wide space access, and across the caller&#x27;s readable spaces otherwise; is_space_filtered says which, and the two are not comparable. |
**metered_open_count** | **object** | usage_daily.obligation_open_count for that day, or null when the reconcile has not written for it yet. Null is not zero: an unwritten day and a tenant with no open obligations are different facts. | [optional]
**metered_reconciled_at** | **object** | When the stock reconcile last wrote for this tenant-day, or null when it never has. This, and not the count, is what says whether the metered figure is a measurement: obligation_open_count is not-null with a default of 0, so a tenant that merely made a request that day carries a zero nothing measured. | [optional]
**usage_date** | **object** | The metered day, in UTC, the stock figure was read for. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

