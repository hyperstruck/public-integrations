# DeclineRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_name** | **object** | Human-readable agent name, unique within your tenant. This is not the hosted agent UUID used in &#x60;/agents/{agent_id}&#x60; REST paths. If no agent with this name exists yet, the platform creates one automatically on the first boundary call (a minimal learning agent scoped to your tenant). Reuse the same name on resolve, observe, reinforce, and distill to target the same learning corpus. Clients conventionally namespace an agent-loop &#x60;run_id&#x60; as &#x60;&lt;agent_name&gt;:...&#x60;; if yours does, avoid the name &#x60;distill&#x60;, because &#x60;distill:&#x60; is reserved for corpus distillation run ids and every agent-loop write would be refused. |
**is_delivered** | **object** | Whether the recall was actually delivered to the model this turn. A turn can receive the injection and still decline, so this decides whether the resolve is billed or released: the caller is charged for recall it received, never for recall it never saw. | [optional]
**org_id** | **object** | Optional caller-owned organisation reference. | [optional]
**reason** | [**DeclineReason**](DeclineReason.md) | Why the turn had nothing worth learning from. |
**run_id** | **object** | The caller-owned &#x60;run_id&#x60; supplied to resolve; it must not start with &#x60;distill:&#x60;, which is reserved for distillation jobs. |
**source_framework** | **object** | Producing host/framework, used to attribute the per-host funnel. Optional; the server derives one when it is absent. &#x60;unknown&#x60; is reserved: the loop-closure funnel groups runs with no attribution under that label and excludes them from alerting, so a value equal to it is normalised to unset rather than stored as a host. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

