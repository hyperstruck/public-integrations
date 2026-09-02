# ParticipantModel

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**attended** | **object** |  | [optional]
**domain** | **object** | The participant&#x27;s registrable domain, when you have no address to send. Reduced to its registrable form on arrival; a value with none (&#x60;corp.local&#x60;, an IP) is dropped from this participant, and an address here is refused. Derived from &#x60;email&#x60; when both are sent. | [optional]
**email** | **object** | The participant&#x27;s address, bare (&#x60;dave@northwindclinics.example&#x60;). Split at the platform into a keyed pseudonym and a registrable domain; the runtime never receives it. The learning boundary drops it there; the documents API keeps it with the document, to show on the document&#x27;s own page, and erases it with the document. One that is not a bare address is refused. | [optional]
**email_authentication** | **object** | What your mail system found when it checked this sender (SPF, DKIM or DMARC): &#x60;passed&#x60;, &#x60;failed&#x60; or &#x60;not_checked&#x60;. A &#x60;from&#x60; participant counts as one of your own people only when &#x60;is_internal&#x60; is true and this is &#x60;passed&#x60;, because a forged address is how a payment instruction is faked. Leave it out when you have no result, and the sender is read as an outside party. | [optional]
**invited** | **object** |  | [optional]
**is_internal** | **object** | Whether this domain is your own. Only you know that, and the flag can only narrow what is learned from the participant, never widen it. | [optional]
**kind** | [**ParticipantKind**](ParticipantKind.md) |  | [optional]
**name** | **object** | The participant&#x27;s display name. An address sent here (&#x60;dave@northwindclinics.example&#x60;, or &#x60;Dave Smith &lt;dave@northwindclinics.example&gt;&#x60;) is taken as the email when none is sent, and only the display part is kept. | [optional]
**organisation** | **object** | The company the source says this address belongs to. A stated pairing, and one of the two things that can license a domain as an organisation&#x27;s own identifier. An address here is refused. | [optional]
**response** | [**ParticipantResponse**](ParticipantResponse.md) |  | [optional]
**role** | [**ParticipantRole**](ParticipantRole.md) |  | [optional]
**speaker_ref** | **object** | The speaker label a transcript used for them. An address here is refused. | [optional]
**spoke** | **object** |  | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

