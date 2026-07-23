# ObserveRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_name** | **object** | Human-readable agent name, unique within your tenant. Not the hosted agent UUID used in `/agents/{agent_id}` REST paths. If no agent with this name exists yet, the platform creates one automatically on the first boundary call. Reuse the same name to target the same learning corpus. |
**org_id** | **object** | Optional caller-owned organisation reference. | [optional]
**episode** | [**EpisodeModel**](EpisodeModel.md) | Caller-supplied completed episode. Direct API clients may construct it without LangGraph. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

