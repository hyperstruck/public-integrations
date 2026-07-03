# hyperstruck.AuthApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**me_me_get**](AuthApi.md#me_me_get) | **GET** /me | Me

# **me_me_get**
> MeResponse me_me_get()

Me

Return the current portal session: user, active tenant, memberships, scopes.  Portal-session only. API-key callers have no portal identity and are rejected with 403 — they should use the resource APIs directly, not `/me`. A valid session without an active membership surfaces as 403 from the middleware.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.AuthApi()

try:
    # Me
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

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

