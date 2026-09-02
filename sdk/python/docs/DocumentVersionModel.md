# DocumentVersionModel

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**created_at** | **object** |  | [optional]
**document_type** | **object** |  |
**previous_version** | **object** |  | [optional]
**relation** | **object** | What this version does to its predecessor. Defaults to &#x60;amends&#x60;, so an ordinary re-upload retires nothing. |
**retention_class** | **object** |  |
**size_bytes** | **object** |  |
**state** | **object** | Core&#x27;s VersionState for this version. |
**version** | **object** | The version&#x27;s identity: the sha256 of the submitted bytes. |

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

