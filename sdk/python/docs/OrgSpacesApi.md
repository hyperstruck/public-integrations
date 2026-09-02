# hyperstruck.OrgSpacesApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_org_space_endpoint_org_org_id_spaces_post**](OrgSpacesApi.md#create_org_space_endpoint_org_org_id_spaces_post) | **POST** /org/{org_id}/spaces | Create Org Space
[**delete_org_space_endpoint_org_org_id_spaces_space_id_delete**](OrgSpacesApi.md#delete_org_space_endpoint_org_org_id_spaces_space_id_delete) | **DELETE** /org/{org_id}/spaces/{space_id} | Delete Org Space
[**invite_space_member_endpoint_org_org_id_spaces_space_id_members_post**](OrgSpacesApi.md#invite_space_member_endpoint_org_org_id_spaces_space_id_members_post) | **POST** /org/{org_id}/spaces/{space_id}/members | Invite Space Member
[**list_space_members_endpoint_org_org_id_spaces_space_id_members_get**](OrgSpacesApi.md#list_space_members_endpoint_org_org_id_spaces_space_id_members_get) | **GET** /org/{org_id}/spaces/{space_id}/members | List Space Members
[**revoke_space_member_endpoint_org_org_id_spaces_space_id_members_identity_user_id_delete**](OrgSpacesApi.md#revoke_space_member_endpoint_org_org_id_spaces_space_id_members_identity_user_id_delete) | **DELETE** /org/{org_id}/spaces/{space_id}/members/{identity_user_id} | Revoke Space Member

# **create_org_space_endpoint_org_org_id_spaces_post**
> SpaceResponse create_org_space_endpoint_org_org_id_spaces_post(body, org_id)

Create Org Space

Create a domain space in the organization, with the caller seeded as steward. Requires developer role or higher.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# Configure API key authorization: PortalSessionCookie
configuration = hyperstruck.Configuration()
configuration.api_key['Cookie'] = 'YOUR_API_KEY'
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['Cookie'] = 'Bearer'

# create an instance of the API class
api_instance = hyperstruck.OrgSpacesApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.CreateSpaceRequest() # CreateSpaceRequest |
org_id = NULL # object | Organization UUID (same as the caller's active tenant id). A foreign org id returns 404.

try:
    # Create Org Space
    api_response = api_instance.create_org_space_endpoint_org_org_id_spaces_post(body, org_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling OrgSpacesApi->create_org_space_endpoint_org_org_id_spaces_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**CreateSpaceRequest**](CreateSpaceRequest.md)|  |
 **org_id** | [**object**](.md)| Organization UUID (same as the caller&#x27;s active tenant id). A foreign org id returns 404. |

### Return type

[**SpaceResponse**](SpaceResponse.md)

### Authorization

[PortalSessionCookie](../README.md#PortalSessionCookie)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **delete_org_space_endpoint_org_org_id_spaces_space_id_delete**
> delete_org_space_endpoint_org_org_id_spaces_space_id_delete(org_id, space_id)

Delete Org Space

Permanently delete a domain space. Requires space steward (org admins qualify). Rejected with 409 while the space still homes agents; only kind='domain' spaces are deletable.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# Configure API key authorization: PortalSessionCookie
configuration = hyperstruck.Configuration()
configuration.api_key['Cookie'] = 'YOUR_API_KEY'
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['Cookie'] = 'Bearer'

# create an instance of the API class
api_instance = hyperstruck.OrgSpacesApi(hyperstruck.ApiClient(configuration))
org_id = NULL # object | Organization UUID (same as the caller's active tenant id). A foreign org id returns 404.
space_id = NULL # object | Space UUID returned by the spaces list or create endpoint.

try:
    # Delete Org Space
    api_instance.delete_org_space_endpoint_org_org_id_spaces_space_id_delete(org_id, space_id)
except ApiException as e:
    print("Exception when calling OrgSpacesApi->delete_org_space_endpoint_org_org_id_spaces_space_id_delete: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **org_id** | [**object**](.md)| Organization UUID (same as the caller&#x27;s active tenant id). A foreign org id returns 404. |
 **space_id** | [**object**](.md)| Space UUID returned by the spaces list or create endpoint. |

### Return type

void (empty response body)

### Authorization

[PortalSessionCookie](../README.md#PortalSessionCookie)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **invite_space_member_endpoint_org_org_id_spaces_space_id_members_post**
> SpaceMemberResponse invite_space_member_endpoint_org_org_id_spaces_space_id_members_post(body, org_id, space_id)

Invite Space Member

Grant an org member a direct role on this space (default 'contributor'). Requires space steward. Domain spaces: any steward. Non-domain spaces: org admin/owner only (intentional override for personal/commons/department). The invitee must already hold an active membership in this organization.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# Configure API key authorization: PortalSessionCookie
configuration = hyperstruck.Configuration()
configuration.api_key['Cookie'] = 'YOUR_API_KEY'
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['Cookie'] = 'Bearer'

# create an instance of the API class
api_instance = hyperstruck.OrgSpacesApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.SpaceMemberInviteRequest() # SpaceMemberInviteRequest |
org_id = NULL # object | Organization UUID (same as the caller's active tenant id). A foreign org id returns 404.
space_id = NULL # object | Space UUID returned by the spaces list or create endpoint.

try:
    # Invite Space Member
    api_response = api_instance.invite_space_member_endpoint_org_org_id_spaces_space_id_members_post(body, org_id, space_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling OrgSpacesApi->invite_space_member_endpoint_org_org_id_spaces_space_id_members_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**SpaceMemberInviteRequest**](SpaceMemberInviteRequest.md)|  |
 **org_id** | [**object**](.md)| Organization UUID (same as the caller&#x27;s active tenant id). A foreign org id returns 404. |
 **space_id** | [**object**](.md)| Space UUID returned by the spaces list or create endpoint. |

### Return type

[**SpaceMemberResponse**](SpaceMemberResponse.md)

### Authorization

[PortalSessionCookie](../README.md#PortalSessionCookie)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_space_members_endpoint_org_org_id_spaces_space_id_members_get**
> SpaceMemberListResponse list_space_members_endpoint_org_org_id_spaces_space_id_members_get(org_id, space_id)

List Space Members

List direct per-user role grants on this space (steward-readable). Userset grants (e.g. commons organization#member) are omitted.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# Configure API key authorization: PortalSessionCookie
configuration = hyperstruck.Configuration()
configuration.api_key['Cookie'] = 'YOUR_API_KEY'
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['Cookie'] = 'Bearer'

# create an instance of the API class
api_instance = hyperstruck.OrgSpacesApi(hyperstruck.ApiClient(configuration))
org_id = NULL # object | Organization UUID (same as the caller's active tenant id). A foreign org id returns 404.
space_id = NULL # object | Space UUID returned by the spaces list or create endpoint.

try:
    # List Space Members
    api_response = api_instance.list_space_members_endpoint_org_org_id_spaces_space_id_members_get(org_id, space_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling OrgSpacesApi->list_space_members_endpoint_org_org_id_spaces_space_id_members_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **org_id** | [**object**](.md)| Organization UUID (same as the caller&#x27;s active tenant id). A foreign org id returns 404. |
 **space_id** | [**object**](.md)| Space UUID returned by the spaces list or create endpoint. |

### Return type

[**SpaceMemberListResponse**](SpaceMemberListResponse.md)

### Authorization

[PortalSessionCookie](../README.md#PortalSessionCookie)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **revoke_space_member_endpoint_org_org_id_spaces_space_id_members_identity_user_id_delete**
> revoke_space_member_endpoint_org_org_id_spaces_space_id_members_identity_user_id_delete(org_id, space_id, identity_user_id)

Revoke Space Member

Remove every direct role a member holds on this space. Requires space steward.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# Configure API key authorization: PortalSessionCookie
configuration = hyperstruck.Configuration()
configuration.api_key['Cookie'] = 'YOUR_API_KEY'
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['Cookie'] = 'Bearer'

# create an instance of the API class
api_instance = hyperstruck.OrgSpacesApi(hyperstruck.ApiClient(configuration))
org_id = NULL # object | Organization UUID (same as the caller's active tenant id). A foreign org id returns 404.
space_id = NULL # object | Space UUID returned by the spaces list or create endpoint.
identity_user_id = NULL # object | Identity user UUID for an organization member.

try:
    # Revoke Space Member
    api_instance.revoke_space_member_endpoint_org_org_id_spaces_space_id_members_identity_user_id_delete(org_id, space_id, identity_user_id)
except ApiException as e:
    print("Exception when calling OrgSpacesApi->revoke_space_member_endpoint_org_org_id_spaces_space_id_members_identity_user_id_delete: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **org_id** | [**object**](.md)| Organization UUID (same as the caller&#x27;s active tenant id). A foreign org id returns 404. |
 **space_id** | [**object**](.md)| Space UUID returned by the spaces list or create endpoint. |
 **identity_user_id** | [**object**](.md)| Identity user UUID for an organization member. |

### Return type

void (empty response body)

### Authorization

[PortalSessionCookie](../README.md#PortalSessionCookie)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

