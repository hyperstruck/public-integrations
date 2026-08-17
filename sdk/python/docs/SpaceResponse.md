# SpaceResponse

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_count** | **object** | How many agents currently home in this space. |
**caller_is_steward** | **object** | True when the authenticated caller may steward this space: a direct steward grant, personal-space owner (creator), or org admin/owner (steward via org admin). Used by the portal for manage-member UX. | [optional]
**created_at** | **object** |  |
**department_id** | **object** | WorkOS directory group id; set iff kind &#x3D;&#x3D; &#x27;department&#x27;. | [optional]
**id** | **object** |  |
**kind** | [**SpaceKind**](SpaceKind.md) |  |
**name** | **object** |  |
**owner_identity_user_id** | **object** | Steward identity user id; set iff kind &#x3D;&#x3D; &#x27;personal&#x27;. | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)

