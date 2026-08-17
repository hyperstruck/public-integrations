# ReinforceRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_name** | **object** | Human-readable agent name, unique within your tenant. This is not the hosted agent UUID used in &#x60;/agents/{agent_id}&#x60; REST paths. If no agent with this name exists yet, the platform creates one automatically on the first boundary call (a minimal learning agent scoped to your tenant). Reuse the same name on resolve, observe, reinforce, and distill to target the same learning corpus. Clients conventionally namespace an agent-loop &#x60;run_id&#x60; as &#x60;&lt;agent_name&gt;:...&#x60;; if yours does, avoid the name &#x60;distill&#x60;, because &#x60;distill:&#x60; is reserved for corpus distillation run ids and every agent-loop write would be refused. |
**context_receipt** | **object** | The host&#x27;s record of the context block as its editor accepted it, used to confirm which offered learnings the model was actually shown. A learning no receipt reports as rendered credits nothing, so a host that omits this earns no reinforcement. Send the artefact the editor produced, never the text this client emitted: an echo of what was sent asserts the very thing the receipt exists to evidence. An over-cap receipt is clipped when folded rather than refused, because refusing it would cost the run its whole reinforcement and not merely its evidence; the bound on this field is far above that clip and exists only to stop an unbounded body. | [optional]
**episode** | [**EpisodeModel**](EpisodeModel.md) | Completed episode using the same caller-owned &#x60;run_id&#x60; supplied to resolve. |
**is_org_promotion_allowed** | **object** | Whether eligible learnings may be considered for organisation sharing. | [optional]
**org_id** | **object** | Optional caller-owned organisation reference. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

