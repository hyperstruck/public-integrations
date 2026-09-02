# DocumentResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**author** | **object** | The name of the first participant who originated the record: one declared with any of the roles &#x60;organiser&#x60;, &#x60;from&#x60;, &#x60;author&#x60;, &#x60;requester&#x60;, &#x60;reporter&#x60;. Absent when none is declared or it has no name. Present with or without a title. | [optional]
**channel** | **object** | The route it travelled, as its list item says. | [optional]
**container_name** | **object** | Its thread&#x27;s name, as its list item says. | [optional]
**doc_id** | **object** |  |
**effects** | **object** | What the document did to the agent&#x27;s claims, as its list item says. Absent for a document not processed, or before the agent&#x27;s claims are replayed; absent is not zero. | [optional]
**extraction_reason** | **object** |  | [optional]
**extraction_state** | **object** | Whether the head version&#x27;s passages have been read into claims. &#x60;failed&#x60; carries &#x60;extraction_reason&#x60; and is retried daily; &#x60;not_eligible&#x60; means this agent&#x27;s claim extraction is off. Absent until a version is stored. | [optional]
**file_name** | **object** | The file name the upload carried. Absent when none was sent. | [optional]
**head_version** | **object** |  | [optional]
**ingest** | **object** | The queue&#x27;s view, read from the job row. Absent when nothing was ever enqueued for this document. | [optional]
**ingest_error** | **object** | Why the last job stopped, when &#x60;ingest&#x60; is &#x60;failed&#x60;. A job cancelled by an erasure reports here too, saying so. | [optional]
**is_effects_unavailable** | **object** | True when the claim store could not be read for this document, as its list item says. Read it again. | [optional]
**note** | **object** |  | [optional]
**occurred_at** | **object** | When the document says it happened, as its list item says. | [optional]
**opening** | **object** | The opening words of the document&#x27;s current text: its first line that has words, passing over code blocks, tables and HTML tags, cut at 80 characters with &#x60;…&#x60; appended when cut. Present only when &#x60;title&#x60; is absent and the text can be read. | [optional]
**reason** | **object** | Why the document is &#x60;failed&#x60; or &#x60;paused&#x60;, as a fixed slug. | [optional]
**record_context** | **object** | The people and containers the sender declared for the head version: who it was from and to, and the channel or thread it was filed under. Kept with the version and erased with it, so an erased document returns none. Null when the sender declared none. | [optional]
**segmenter_version** | **object** |  | [optional]
**state** | **object** | The one state the document list reports for this document. Absent when the document is not among the agent&#x27;s documents, for example after it was deleted. | [optional]
**text_sha256** | **object** | The current text version, which with &#x60;segmenter_version&#x60; opens the text through &#x60;text:window&#x60;. | [optional]
**title** | **object** | The document&#x27;s title: the one declared when it was sent, else for a PDF the one read off its own pages. Absent when it has neither; never the file name. | [optional]
**version_state** | **object** | Core&#x27;s VersionState for the head version. Never conflated with &#x60;ingest&#x60;: &#x60;superseded&#x60; is citable by design and is not a failure. | [optional]
**versions** | **object** |  | [optional]
**zone** | **object** | The zone its times show in, as its list item says. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

