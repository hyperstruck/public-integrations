# hyperstruck.BillingApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_billing_summary_endpoint_billing_summary_get**](BillingApi.md#get_billing_summary_endpoint_billing_summary_get) | **GET** /billing/summary | Get Billing Summary

# **get_billing_summary_endpoint_billing_summary_get**
> BillingSummaryResponse get_billing_summary_endpoint_billing_summary_get()

Get Billing Summary

Return the active tenant's spend limit, billed amount, reserved amount, remaining capacity, and enforcement window. Use it before dispatching optional work when the integration needs to display budget status.

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
api_instance = hyperstruck.BillingApi(hyperstruck.ApiClient(configuration))

try:
    # Get Billing Summary
    api_response = api_instance.get_billing_summary_endpoint_billing_summary_get()
    pprint(api_response)
except ApiException as e:
    print("Exception when calling BillingApi->get_billing_summary_endpoint_billing_summary_get: %s\n" % e)
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**BillingSummaryResponse**](BillingSummaryResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

