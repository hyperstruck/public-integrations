# ObligationResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_id** | **object** |  |
**closed_at** | **object** |  |
**committed_at** | **object** |  |
**created_at** | **object** |  |
**dedupe_key** | **object** |  |
**delivered_count** | **object** |  |
**dropped_reason** | **object** |  |
**due_at** | **object** | The first instant the obligation is overdue. When due_precision is &#x27;date&#x27;, that is the start of the day after due_local in due_tz, one day ahead of the day that was meant. Returned as stored, not converted: render due_local instead. |
**due_from_claim_id** | **object** |  |
**due_local** | **object** | due_at rendered for the caller. When due_precision is &#x27;date&#x27;, this is the due DAY as &#x27;YYYY-MM-DD&#x27; in the due&#x27;s own zone. When due_precision is &#x27;datetime&#x27;, this is the ISO instant converted into the requested (or agent default) zone. | [optional]
**due_precision** | **object** |  |
**due_tz** | **object** | The due&#x27;s own zone: an IANA zone or, when that is all the source gave, a fixed offset. |
**due_tz_basis** | **object** | Where due_tz came from: &#x27;phrase&#x27; (the due phrase named a zone), &#x27;note&#x27; (the note declared one), &#x27;agent&#x27; (the agent&#x27;s default), &#x27;offset&#x27; (the note&#x27;s timestamp offset), &#x27;caller&#x27; (a person set the due), or &#x27;defaulted&#x27; (nothing said, UTC was assumed). Null on rows written before it was recorded. A &#x27;defaulted&#x27; due&#x27;s day may be wrong. | [optional]
**expired_reason** | **object** |  |
**expires_at** | **object** |  |
**id** | **object** |  |
**kept_basis** | **object** |  |
**kind** | **object** | A commitment one party owes, or a meeting owed jointly by its attendees. | [optional]
**last_surfaced_at** | **object** |  |
**later_standing** | **object** | What a LATER note said about this obligation: its kind (already_done, withdrawn or superseded), and the phrase and corpus span it was read from. The row stays open; the flag is a question for a person, never an outcome. | [optional]
**later_standing_at** | **object** |  | [optional]
**lead_days** | **object** |  |
**neglect_flagged_at** | **object** |  |
**not_before** | **object** |  |
**note** | **object** | Only on a single-obligation read, and only for a line harvested from a stored note. Null for every other line and on every list. | [optional]
**org_id** | **object** |  |
**owed_by_entity_id** | **object** |  |
**owed_by_name** | **object** | The obligor&#x27;s canonical name, resolved from the registry at read time rather than copied onto the obligation, so an entity merge or an erasure is honoured by the next read. Null when the party is a bare role, or when the name does not resolve for this caller. | [optional]
**owed_by_role** | **object** |  |
**owed_to_entity_id** | **object** |  |
**owed_to_name** | **object** | The obligee&#x27;s canonical name, resolved the same way as owed_by_name. On the corpus-harvested lane this is who the commitment was made to, and without it a curation surface can only show an opaque id. | [optional]
**owed_to_role** | **object** |  |
**participants** | **object** | Everyone on the obligation when a party was a list: \&quot;Brad and Daniel\&quot; is owed_by Brad with both Brad and Daniel here as owners. Empty when each side names one party. | [optional]
**premise_claim_ids** | **object** |  |
**privacy** | **object** |  |
**provenance** | **object** |  |
**provenance_class** | **object** |  |
**review_reasons** | **object** | Why this obligation is waiting on a person rather than on its due date. Populated only by ?needs_review&#x3D;true; empty on every other read, which makes no claim either way rather than asserting nothing is wrong. One of untrusted_provenance, premise_retracted, later_standing, neglected; a row may carry several. | [optional]
**statement** | **object** |  |
**status** | **object** |  |
**subject_entity_id** | **object** |  |
**subject_name** | **object** | The subject entity&#x27;s canonical name, resolved from the registry at read time. Null when the obligation names no subject, or when the name does not resolve for this caller. | [optional]
**superseded_by** | **object** |  |
**suppression_until** | **object** |  |
**surfaced_count** | **object** |  |
**trigger_kind** | **object** |  |
**updated_at** | **object** |  |
**version** | **object** |  |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

