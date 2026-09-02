# RenewAdmissionRequest

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**declarer_api_key_id** | **object** | The API key allowed to declare this source on an upload. A declaration from any other key raises no trust and is not counted as observed. | [optional]
**declarer_identity_user_id** | **object** | The person allowed to declare this source on an upload, for uploads made in a signed-in session. Name this or an API key, not both. | [optional]
**expires_at** | **object** | New expiry, measured from now. Defaults to 90 days; refused beyond 180 days. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

