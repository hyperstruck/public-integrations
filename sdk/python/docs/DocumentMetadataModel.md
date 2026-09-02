# DocumentMetadataModel

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**channel** | [**StatableChannel**](StatableChannel.md) | Required. How this document reached you, stated by the sender and never guessed. A chat message states &#x60;chat&#x60;; the pages name a chat message by its thread only when this says so. Send &#x60;unknown&#x60; when you do not know. |
**occurred_at** | **object** | When the document happened. Never inferred from the text or the upload time. | [optional]
**record_context** | **object** |  | [optional]
**source_id** | **object** | The system this document came from (&#x60;carrier-portal&#x60;). A space&#x27;s admitted sources are matched against it, so a note from an admitted source is ranked as trusted, but only when the key or person that uploads it is the one the admission names. Refused when no admission could match it: empty, containing &#x27;:&#x27;, a path separator or a dot segment, or over 200 characters. | [optional]
**source_url** | **object** | Where your own system shows this document, an absolute http or https URL. An answer that cites the document links its source line here. Any &#x60;user:password@&#x60; is removed before it is stored; the query string is kept. | [optional]
**timezone** | **object** | The IANA time zone the document was written in (&#x60;Australia/Sydney&#x60;), for a document that states no offset of its own. A time of day or a date it gives is read in this zone, ahead of the agent&#x27;s zone; an offset the document states itself wins over it. A bare offset such as &#x60;+10:00&#x60; is refused, since only a zone name follows daylight saving. | [optional]
**title** | **object** |  | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

