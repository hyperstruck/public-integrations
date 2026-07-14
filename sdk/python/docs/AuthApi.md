# hyperstruck.AuthApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**me_me_get**](AuthApi.md#me_me_get) | **GET** /me | Get Current Portal Identity

# **me_me_get**
> MeResponse me_me_get()

Get Current Portal Identity

Return the signed-in portal user's identity, active tenant, memberships, role, and effective scopes. This endpoint requires a portal session; Bearer API keys should call resource endpoints directly.

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
api_instance = hyperstruck.AuthApi(hyperstruck.ApiClient(configuration))

try:
    # Get Current Portal Identity
    api_response = api_instance.me_me_get()
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AuthApi->me_me_get: %s\n" % e)
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**MeResponse**](MeResponse.md)

### Authorization

[PortalSessionCookie](../README.md#PortalSessionCookie)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

