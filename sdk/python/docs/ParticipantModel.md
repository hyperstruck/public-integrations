# ParticipantModel

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**attended** | **object** |  | [optional]
**domain** | **object** | The participant&#x27;s registrable domain, when you have no address to send. Reduced to its registrable form on arrival; a value with none (&#x60;corp.local&#x60;, an IP) is dropped from this participant, and an address here is refused. Derived from &#x60;email&#x60; when both are sent. | [optional]
**email** | **object** | The participant&#x27;s address, bare (&#x60;dave@northwindclinics.example&#x60;). Split at the platform into a keyed pseudonym and a registrable domain, then dropped: it is never queued, stored or passed to the runtime. One that is not a bare address is refused. | [optional]
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

