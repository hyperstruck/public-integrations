# UsageRunAggregates

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**run_count** | **object** | All runs created in the window. |
**runs_with_compute_count** | **object** | Runs with compute_seconds &gt; 0 (used for average duration). |
**total_compute_seconds** | **object** | Sum of compute_seconds for runs in the window. |
**total_compute_hours** | **object** | total_compute_seconds / 3600. |
**total_estimated_cost_usd** | **object** | Sum of estimated_total_cost_usd (ledger values at completion time). |
**total_estimated_compute_cost_usd** | **object** | Sum of estimated_compute_cost_usd. |
**total_estimated_llm_cost_usd** | **object** | Sum of estimated_llm_cost_usd. |
**average_compute_seconds** | **object** | Mean compute_seconds over runs with compute &gt; 0; null if none. | [optional]
**unique_session_count** | **object** | Distinct non-null session_id values in the window. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

