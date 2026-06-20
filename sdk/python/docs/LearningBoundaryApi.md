# hyperstruck.LearningBoundaryApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**observe_endpoint_v1_observe_post**](LearningBoundaryApi.md#observe_endpoint_v1_observe_post) | **POST** /v1/observe | Observe a finished episode
[**reinforce_endpoint_v1_reinforce_post**](LearningBoundaryApi.md#reinforce_endpoint_v1_reinforce_post) | **POST** /v1/reinforce | Reinforce the learnings a run used
[**resolve_endpoint_v1_resolve_post**](LearningBoundaryApi.md#resolve_endpoint_v1_resolve_post) | **POST** /v1/resolve | Resolve the learnings bound to a goal

# **observe_endpoint_v1_observe_post**
> BoundaryAcceptedResponse observe_endpoint_v1_observe_post(body)

Observe a finished episode

Submit a finished run for server-side learning extraction. Processed on a background worker, so the request returns immediately. Idempotent by run id.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.LearningBoundaryApi()
body = hyperstruck.ObserveRequest() # ObserveRequest | 

try:
    # Observe a finished episode
    api_response = api_instance.observe_endpoint_v1_observe_post(body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningBoundaryApi->observe_endpoint_v1_observe_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ObserveRequest**](ObserveRequest.md)|  | 

### Return type

[**BoundaryAcceptedResponse**](BoundaryAcceptedResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **reinforce_endpoint_v1_reinforce_post**
> BoundaryAcceptedResponse reinforce_endpoint_v1_reinforce_post(body)

Reinforce the learnings a run used

Credit the learnings a finished run used. The eligible union and attribution are derived server-side from the run's offer log. Processed on a background worker; idempotent by run id.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.LearningBoundaryApi()
body = hyperstruck.ReinforceRequest() # ReinforceRequest | 

try:
    # Reinforce the learnings a run used
    api_response = api_instance.reinforce_endpoint_v1_reinforce_post(body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningBoundaryApi->reinforce_endpoint_v1_reinforce_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ReinforceRequest**](ReinforceRequest.md)|  | 

### Return type

[**BoundaryAcceptedResponse**](BoundaryAcceptedResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **resolve_endpoint_v1_resolve_post**
> ResolveResponse resolve_endpoint_v1_resolve_post(body)

Resolve the learnings bound to a goal

Return the learnings bound to a run's goal, as a rendered injection block plus the offered learning IDs. Records the offer server-side so a later reinforce can credit the learnings the run used.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.LearningBoundaryApi()
body = hyperstruck.ResolveRequest() # ResolveRequest | 

try:
    # Resolve the learnings bound to a goal
    api_response = api_instance.resolve_endpoint_v1_resolve_post(body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningBoundaryApi->resolve_endpoint_v1_resolve_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ResolveRequest**](ResolveRequest.md)|  | 

### Return type

[**ResolveResponse**](ResolveResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

