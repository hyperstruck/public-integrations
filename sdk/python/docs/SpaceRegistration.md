# SpaceRegistration

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**external_id** | **object** | Identifier of the container this space mirrors, unique per organization and per system. Opaque: never validated against the external system and never used to call it. Stored and resolved verbatim, but keyed case-insensitively, so a case-variant of a container this organization already registered is refused rather than admitted as a second space. |
**external_system** | **object** | Label naming whose identifier &#x60;external_id&#x60; is, for example the chat product a channel belongs to. Lower-cased on the way in, because it is part of the per-tenant uniqueness key. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

