# EvidenceItemModel

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**content** | **object** | Primary text; the grounding source extraction quotes from. |
**declared_sensitivity** | **object** | Optional caller-declared metadata for this item, in the same vocabulary as a step&#x27;s. The &#x60;provenance&#x60; record says where the item came from, in two independent facets plus identity: &#x60;channel&#x60; is how it reached you (chat, email, meeting, document_store, system_of_record, api) and conditions how fast it goes stale; &#x60;genre&#x60; is what kind of artefact it is (policy, plan, minutes, reference, correspondence, note, aside) and conditions how authoritative it is. A signed policy pasted into a chat thread is both, which is why they are separate. Also &#x60;source_id&#x60;, &#x60;author&#x60;, and an RFC 3339 &#x60;source_time&#x60; for when the facts in it became true. An unrecognised &#x60;channel&#x60; or &#x60;genre&#x60; is kept verbatim and left unranked rather than refused. &#x60;source_class&#x60; is the superseded single-facet form, still accepted and never ranked. To say what the item is *about*, use the &#x60;subject&#x60; field above rather than this record. | [optional]
**id** | **object** | Stable within the run. |
**label** | **object** | e.g. \&quot;baseline\&quot;, \&quot;fix\&quot;. | [optional]
**role** | **object** |  | [optional]
**source_ref** | **object** | Non-secret provenance: a doc id or URL. | [optional]
**status** | **object** |  | [optional]
**subject** | **object** | The entity this item is about, e.g. an account or product name. Given, it is the name the facts are filed under, which is what stops one entity fragmenting across two spellings and never accumulating corroboration. Omitted, the entity is read from the prose. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

