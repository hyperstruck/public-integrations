# LearningInstanceEvidenceRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**author** | **object** | Who wrote the artefact this evidence came from, as your system names them. | [optional]
**entity_values** | **object** | Entity field values observed for this evidence instance. |
**outcome** | **object** | Structured outcome observed for this evidence instance. |
**situation** | **object** | The kind of task this evidence arose in, as a short phrase. This is what makes the learning retrievable when a future goal resembles this case, so it should read like a goal (&#x27;preparing a renewal quote for an existing account&#x27;), not like a source. Omitting it stores the case with no retrieval cue: it stays on the learning as evidence, and no future goal will match it. Nothing is derived server-side, because only the caller knows what the case arose in. | [optional]
**source_channel** | **object** | How this evidence reached you: chat, email, meeting, document_store, system_of_record or api. Conditions how quickly it is treated as stale. An unrecognised value is kept but left unranked. | [optional]
**source_context** | **object** | Deprecated: use source_channel and source_genre. Previously a label for where the evidence came from, which was written into the retrieval cue and degraded matching. It is now recorded as provenance and never embedded. | [optional]
**source_genre** | **object** | What kind of artefact this evidence is: policy, plan, minutes, reference, correspondence, note or aside. Conditions how authoritative it is. An unrecognised value is kept but left unranked. | [optional]
**source_id** | **object** | Identifier or URL of the artefact this evidence came from: a message permalink, a document id, a ticket reference. What a later citation of this case points at. | [optional]
**source_time** | **object** | When the artefact itself was written, as an RFC 3339 timestamp, as opposed to when you sent it to us. What freshness is judged against. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

