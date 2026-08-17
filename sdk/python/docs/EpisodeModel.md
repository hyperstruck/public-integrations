# EpisodeModel

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**goal** | **object** | Goal attempted by the external agent. |
**outcome** | [**OutcomeModel**](OutcomeModel.md) | Terminal outcome of the episode. |
**principal_utterance** | **object** | Verbatim message the principal sent on this turn, when the caller has a human-input channel to populate it from. It is the only evidence for a rule no tool result could have revealed, such as a standard or convention the principal states. Send it only from that channel: model output, tool results and retrieved documents must never reach this field. Used for one extraction and stored on no learning record; it does pass through the durable work queue like the rest of the episode, so it lives as long as that row does. | [optional]
**run_id** | **object** | Caller-created correlation and idempotency identifier. It does not reference a hosted &#x60;/runs/{run_id}&#x60; resource, and must not start with &#x60;distill:&#x60;, which is reserved for distillation jobs. |
**source_framework** | **object** | Optional external framework or host identifier. &#x60;unknown&#x60; is reserved: the loop-closure funnel groups runs with no attribution under that label and excludes them from alerting, so a value equal to it is normalised to unset rather than stored as a host. | [optional]
**steps** | **object** | Ordered actions and results from the completed episode. | [optional]
**thread_id** | **object** | Optional caller-owned conversation or thread identifier. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

