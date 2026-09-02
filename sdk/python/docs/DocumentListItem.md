# DocumentListItem

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**arrived_at** | **object** | When the newest upload of this document was accepted. |
**author** | **object** | The name of the first participant who originated the record: one declared with any of the roles &#x60;organiser&#x60;, &#x60;from&#x60;, &#x60;author&#x60;, &#x60;requester&#x60;, &#x60;reporter&#x60;. Absent when none is declared or it has no name. Present with or without a title. | [optional]
**channel** | **object** | How the document travelled: the route its sender stated, or &#x60;web&#x60; for a page a crawl or URL watch fetched, which no sender stated. Absent for a document stored without one. | [optional]
**container_name** | **object** | What a person calls the thread the document belongs to (a channel&#x27;s name), as its sender declared it. Absent when none was declared. | [optional]
**doc_id** | **object** |  |
**document_type** | **object** |  | [optional]
**effects** | **object** | What a processed document did to the agent&#x27;s claims, as the claim store counts it now. Absent for a document not processed, or before the agent&#x27;s claims are replayed; absent is not zero. | [optional]
**file_name** | **object** | The file name the upload carried. Absent when none was sent. | [optional]
**is_effects_unavailable** | **object** | True when the claim store could not be read for this list, so a processed document&#x27;s &#x60;effects&#x60; are absent for that reason and not because it awaits processing. Read the list again. | [optional]
**note** | **object** | Something to know about a &#x60;ready&#x60; document: a newer version is on its way or failed, its obligations were not read, it is stored for citation only, or only part of it was read. | [optional]
**occurred_at** | **object** |  | [optional]
**opening** | **object** | The opening words of the document&#x27;s current text: its first line that has words, passing over code blocks, tables and HTML tags, cut at 80 characters with &#x60;…&#x60; appended when cut. Present only when &#x60;title&#x60; is absent and the text can be read. | [optional]
**reason** | **object** | Why a document is &#x60;failed&#x60; or &#x60;paused&#x60;, as a fixed slug. Never free text. | [optional]
**size_bytes** | **object** |  | [optional]
**state** | **object** | &#x60;queued&#x60; and &#x60;ingesting&#x60; are on their way. &#x60;ready&#x60; can be cited and its claims were read. &#x60;paused&#x60; was stored and its claims were not read because the spend limit was reached. &#x60;failed&#x60; names why in &#x60;reason&#x60;. |
**title** | **object** | The document&#x27;s title: the one declared when it was sent, else for a PDF the one read off its own pages. Absent when it has neither; never the file name. | [optional]
**zone** | **object** | The IANA zone the document&#x27;s own times were read in, which its time shows in. Absent before the agent&#x27;s claims are replayed. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

