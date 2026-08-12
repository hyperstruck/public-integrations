# hyperstruck.OrgDirectoryApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**list_org_directory_endpoint_org_org_id_directory_get**](OrgDirectoryApi.md#list_org_directory_endpoint_org_org_id_directory_get) | **GET** /org/{org_id}/directory | List Org Directory

# **list_org_directory_endpoint_org_org_id_directory_get**
> OrgDirectoryListResponse list_org_directory_endpoint_org_org_id_directory_get(org_id, limit=limit, cursor=cursor)

List Org Directory

List active organization members for invite pickers: identity_user_id, email, and display_name only. Available to any org member (not just admins). Cursor-paginated on membership created_at.

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
api_instance = hyperstruck.OrgDirectoryApi(hyperstruck.ApiClient(configuration))
org_id = NULL # object | Organization UUID (same as the caller's active tenant id). A foreign org id returns 404.
limit = 50 # object | Maximum number of items to return on this page. (optional) (default to 50)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)

try:
    # List Org Directory
    api_response = api_instance.list_org_directory_endpoint_org_org_id_directory_get(org_id, limit=limit, cursor=cursor)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling OrgDirectoryApi->list_org_directory_endpoint_org_org_id_directory_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **org_id** | [**object**](.md)| Organization UUID (same as the caller&#x27;s active tenant id). A foreign org id returns 404. |
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 50]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]

### Return type

[**OrgDirectoryListResponse**](OrgDirectoryListResponse.md)

### Authorization

[PortalSessionCookie](../README.md#PortalSessionCookie)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

