# hyperstruck.BillingApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_billing_summary_endpoint_billing_summary_get**](BillingApi.md#get_billing_summary_endpoint_billing_summary_get) | **GET** /billing/summary | Get Billing Summary Endpoint

# **get_billing_summary_endpoint_billing_summary_get**
> BillingSummaryResponse get_billing_summary_endpoint_billing_summary_get()

Get Billing Summary Endpoint

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.BillingApi()

try:
    # Get Billing Summary Endpoint
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

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

