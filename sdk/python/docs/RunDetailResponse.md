# RunDetailResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_id** | **object** | Hosted agent UUID associated with this run. | [optional]
**compute_seconds** | **object** |  |
**created_at** | **object** |  |
**ended_at** | **object** |  |
**error** | **object** |  |
**estimated_compute_cost_usd** | **object** |  |
**estimated_total_cost_usd** | **object** |  | [optional]
**goal** | **object** |  |
**id** | **object** | Server-issued hosted run UUID used by &#x60;/runs/{run_id}&#x60;. |
**input** | [**RunInputSummary**](RunInputSummary.md) |  |
**metadata** | **object** |  | [optional]
**output** | [**RunOutputSummary**](RunOutputSummary.md) |  |
**parent_run_id** | **object** | Parent hosted run UUID when this run resumed a suspension. | [optional]
**run_type** | [**RunType**](RunType.md) |  |
**session_id** | **object** | Conversation session UUID, when the run belongs to a session. |
**started_at** | **object** |  |
**status** | [**RunStatus**](RunStatus.md) |  |
**worker_profile** | **object** |  |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

