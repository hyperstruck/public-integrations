# hyperstruck.EntitlementsApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**entitlements_endpoint_entitlements_get**](EntitlementsApi.md#entitlements_endpoint_entitlements_get) | **GET** /entitlements | The calling principal&#x27;s plan entitlements

# **entitlements_endpoint_entitlements_get**
> EntitlementsResponse entitlements_endpoint_entitlements_get()

The calling principal's plan entitlements

Return the authenticated caller's plan code, compliance add-on flag, and granted scopes (implied scopes expanded). Scoped to the caller's own principal.

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
api_instance = hyperstruck.EntitlementsApi(hyperstruck.ApiClient(configuration))

try:
    # The calling principal's plan entitlements
    api_response = api_instance.entitlements_endpoint_entitlements_get()
    pprint(api_response)
except ApiException as e:
    print("Exception when calling EntitlementsApi->entitlements_endpoint_entitlements_get: %s\n" % e)
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**EntitlementsResponse**](EntitlementsResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

