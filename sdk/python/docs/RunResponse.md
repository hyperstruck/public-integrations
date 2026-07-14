# RunResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **object** | Server-issued hosted run UUID used by &#x60;/runs/{run_id}&#x60;. |
**agent_id** | **object** | Hosted agent UUID associated with this run. | [optional]
**session_id** | **object** | Conversation session UUID, when the run belongs to a session. |
**parent_run_id** | **object** | Parent hosted run UUID when this run resumed a suspension. | [optional]
**run_type** | [**RunType**](RunType.md) |  |
**status** | [**RunStatus**](RunStatus.md) |  |
**goal** | **object** |  |
**worker_profile** | **object** |  |
**started_at** | **object** |  |
**ended_at** | **object** |  |
**compute_seconds** | **object** |  |
**estimated_compute_cost_usd** | **object** |  |
**estimated_total_cost_usd** | **object** |  | [optional]
**error** | **object** |  |
**metadata** | **object** |  | [optional]
**created_at** | **object** |  |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

