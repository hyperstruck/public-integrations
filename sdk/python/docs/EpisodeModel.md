# EpisodeModel

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**available_tools** | **object** | The tools the agent had available during this episode, with their declared categories and shapes. Left empty, tool-aware retrieval writes an empty fingerprint and restraint cannot be read at all. | [optional]
**goal** | **object** | Goal attempted by the external agent. |
**occurred_at** | **object** | RFC 3339 time this run actually spoke, offset required. Omit it and the boundary stamps its own arrival instead, which is fine for learning decay and wrong for obligations: a commitment harvested from final_output is anchored on this instant and stored as anchor_kind &#x60;run_clock&#x60;, which means the moment the agent said it, not the moment we received it. A client that stages a turn and flushes it later must send this, or \&quot;by Friday\&quot; resolves against the flush and lands on the wrong day. Carry the offset: a date-only deadline belongs to a calendar day in the speaker&#x27;s own zone, and a bare timestamp is read in ours. | [optional]
**outcome** | [**OutcomeModel**](OutcomeModel.md) | Terminal outcome of the episode. |
**principal_utterance** | **object** | Verbatim message the principal sent on this turn, when the caller has a human-input channel to populate it from. It is the only evidence for a rule no tool result could have revealed, such as a standard or convention the principal states. Send it only from that channel: model output, tool results and retrieved documents must never reach this field. Used for one extraction and stored on no learning record; it does pass through the durable work queue like the rest of the episode, so it lives as long as that row does. | [optional]
**run_id** | **object** | Caller-created correlation and idempotency identifier. It does not reference a hosted &#x60;/runs/{run_id}&#x60; resource, and must not start with &#x60;distill:&#x60;, which is reserved for distillation jobs. |
**source_framework** | **object** | Optional external framework or host identifier. &#x60;unknown&#x60; is reserved: the loop-closure funnel groups runs with no attribution under that label and excludes them from alerting, so a value equal to it is normalised to unset rather than stored as a host. | [optional]
**spans** | **object** | How the caller cut &#x60;goal&#x60; into prose and machine markup, when it knows. Omit it and the goal is labelled from a closed set of markup this platform recognises, which is right for a caller that cannot say and incomplete for a host whose own envelope that set does not carry. Spans are matched to the goal by content and in order; text left between them is labelled by the closed set and counted as a gap. Only &#x60;goal&#x60; is read from this: step results, errors and the composed answer are labelled by the closed set whatever is sent here. | [optional]
**steps** | **object** | Ordered actions and results from the completed episode. | [optional]
**thread_id** | **object** | Optional caller-owned conversation or thread identifier. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

