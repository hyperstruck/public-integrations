# hyperstruck.OrgMembersApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**list_org_members_endpoint_org_org_id_members_get**](OrgMembersApi.md#list_org_members_endpoint_org_org_id_members_get) | **GET** /org/{org_id}/members | List Org Members
[**update_org_member_role_endpoint_org_org_id_members_identity_user_id_patch**](OrgMembersApi.md#update_org_member_role_endpoint_org_org_id_members_identity_user_id_patch) | **PATCH** /org/{org_id}/members/{identity_user_id} | Change Org Member Role

# **list_org_members_endpoint_org_org_id_members_get**
> OrgMemberListResponse list_org_members_endpoint_org_org_id_members_get(org_id, limit=limit, cursor=cursor)

List Org Members

List the organization's members (admin/owner only), excluding disabled accounts. `space_memberships` reports each member's direct/explicit space grants only (never implied commons/org-admin access). Cursor-paginated on `created_at`.

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
api_instance = hyperstruck.OrgMembersApi(hyperstruck.ApiClient(configuration))
org_id = NULL # object | Organization UUID (same as the caller's active tenant id). A foreign org id returns 404.
limit = 50 # object | Maximum number of items to return on this page. (optional) (default to 50)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)

try:
    # List Org Members
    api_response = api_instance.list_org_members_endpoint_org_org_id_members_get(org_id, limit=limit, cursor=cursor)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling OrgMembersApi->list_org_members_endpoint_org_org_id_members_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **org_id** | [**object**](.md)| Organization UUID (same as the caller&#x27;s active tenant id). A foreign org id returns 404. |
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 50]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]

### Return type

[**OrgMemberListResponse**](OrgMemberListResponse.md)

### Authorization

[PortalSessionCookie](../README.md#PortalSessionCookie)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **update_org_member_role_endpoint_org_org_id_members_identity_user_id_patch**
> OrgMemberRoleUpdateResponse update_org_member_role_endpoint_org_org_id_members_identity_user_id_patch(body, org_id, identity_user_id)

Change Org Member Role

Change a member's role (admin/owner only). Role safety rules: a caller cannot change their own role, only an owner may assign the owner role, an admin may not modify another owner's role, and the last active owner cannot be demoted.

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
api_instance = hyperstruck.OrgMembersApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.OrgMemberRoleUpdateRequest() # OrgMemberRoleUpdateRequest |
org_id = NULL # object | Organization UUID (same as the caller's active tenant id). A foreign org id returns 404.
identity_user_id = NULL # object | Identity user UUID for an organization member.

try:
    # Change Org Member Role
    api_response = api_instance.update_org_member_role_endpoint_org_org_id_members_identity_user_id_patch(body, org_id, identity_user_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling OrgMembersApi->update_org_member_role_endpoint_org_org_id_members_identity_user_id_patch: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**OrgMemberRoleUpdateRequest**](OrgMemberRoleUpdateRequest.md)|  |
 **org_id** | [**object**](.md)| Organization UUID (same as the caller&#x27;s active tenant id). A foreign org id returns 404. |
 **identity_user_id** | [**object**](.md)| Identity user UUID for an organization member. |

### Return type

[**OrgMemberRoleUpdateResponse**](OrgMemberRoleUpdateResponse.md)

### Authorization

[PortalSessionCookie](../README.md#PortalSessionCookie)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

