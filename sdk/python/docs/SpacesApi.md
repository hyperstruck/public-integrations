# hyperstruck.SpacesApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**list_spaces_endpoint_spaces_get**](SpacesApi.md#list_spaces_endpoint_spaces_get) | **GET** /spaces | List Spaces

# **list_spaces_endpoint_spaces_get**
> SpaceListResponse list_spaces_endpoint_spaces_get(limit=limit, cursor=cursor, _for=_for)

List Spaces

List spaces in the active tenant. Default (`for=read`) returns spaces the caller can read. Pass `for=publish` for spaces the caller may publish to (agent home-space picker). When `for=publish`, personal spaces owned by other users are excluded.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# Configure API key authorization: BearerApiKey
configuration = hyperstruck.Configuration()
configuration.api_key['Authorization'] = 'YOUR_API_KEY'
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['Authorization'] = 'Bearer'

# create an instance of the API class
api_instance = hyperstruck.SpacesApi(hyperstruck.ApiClient(configuration))
limit = 50 # object | Maximum number of items to return on this page. (optional) (default to 50)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)
_for = read # object | `read` (default): readable spaces. `publish`: spaces the caller may publish to (home-space picker). (optional) (default to read)

try:
    # List Spaces
    api_response = api_instance.list_spaces_endpoint_spaces_get(limit=limit, cursor=cursor, _for=_for)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling SpacesApi->list_spaces_endpoint_spaces_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 50]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]
 **_for** | [**object**](.md)| &#x60;read&#x60; (default): readable spaces. &#x60;publish&#x60;: spaces the caller may publish to (home-space picker). | [optional] [default to read]

### Return type

[**SpaceListResponse**](SpaceListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

