# hyperstruck.LearningBoundaryApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**distill_endpoint_distill_post**](LearningBoundaryApi.md#distill_endpoint_distill_post) | **POST** /distill | Distil learnings from a corpus of evidence
[**funnel_endpoint_funnel_get**](LearningBoundaryApi.md#funnel_endpoint_funnel_get) | **GET** /funnel | Per-host loop-closure funnel
[**observe_endpoint_observe_post**](LearningBoundaryApi.md#observe_endpoint_observe_post) | **POST** /observe | Observe a finished episode
[**reinforce_endpoint_reinforce_post**](LearningBoundaryApi.md#reinforce_endpoint_reinforce_post) | **POST** /reinforce | Reinforce the learnings a run used
[**resolve_endpoint_resolve_post**](LearningBoundaryApi.md#resolve_endpoint_resolve_post) | **POST** /resolve | Resolve the learnings bound to a goal

# **distill_endpoint_distill_post**
> BoundaryAcceptedResponse distill_endpoint_distill_post(body)

Distil learnings from a corpus of evidence

Distil durable learnings from a corpus (post-mortems, docs, diffs, analysis output) by submitting a distillation goal plus evidence items, instead of a tool-step episode. Runs the same server-side extraction as observe on a background worker (202), but stands outside the resolve/observe/reinforce loop. Requires at least two evidence items with enough content to ground a learning, a declared contrast signal (differing status/role, a role='contrast' item, or an evaluation note), and a 'distill:'-prefixed run_id. A corpus that declares contrast but carries none is still accepted and simply yields nothing (a valid 202). Evidence content is stored verbatim where grounded, so callers must pre-redact secrets.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.LearningBoundaryApi()
body = hyperstruck.DistillRequest() # DistillRequest | 

try:
    # Distil learnings from a corpus of evidence
    api_response = api_instance.distill_endpoint_distill_post(body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningBoundaryApi->distill_endpoint_distill_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**DistillRequest**](DistillRequest.md)|  | 

### Return type

[**BoundaryAcceptedResponse**](BoundaryAcceptedResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **funnel_endpoint_funnel_get**
> LoopClosureFunnelResponse funnel_endpoint_funnel_get(window_hours=window_hours, grace_minutes=grace_minutes)

Per-host loop-closure funnel

Report the loop-closure funnel (resolve -> offered -> observed -> reinforced) per producing host over a recent window. A half-open loop, a run that resolved but whose write-back never arrived, shows as a non-closure rather than a false closure. Scoped to the calling tenant.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.LearningBoundaryApi()
window_hours = 24 # object |  (optional) (default to 24)
grace_minutes = 15 # object |  (optional) (default to 15)

try:
    # Per-host loop-closure funnel
    api_response = api_instance.funnel_endpoint_funnel_get(window_hours=window_hours, grace_minutes=grace_minutes)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningBoundaryApi->funnel_endpoint_funnel_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **window_hours** | [**object**](.md)|  | [optional] [default to 24]
 **grace_minutes** | [**object**](.md)|  | [optional] [default to 15]

### Return type

[**LoopClosureFunnelResponse**](LoopClosureFunnelResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **observe_endpoint_observe_post**
> BoundaryAcceptedResponse observe_endpoint_observe_post(body)

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
    api_response = api_instance.observe_endpoint_observe_post(body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningBoundaryApi->observe_endpoint_observe_post: %s\n" % e)
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

# **reinforce_endpoint_reinforce_post**
> BoundaryAcceptedResponse reinforce_endpoint_reinforce_post(body)

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
    api_response = api_instance.reinforce_endpoint_reinforce_post(body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningBoundaryApi->reinforce_endpoint_reinforce_post: %s\n" % e)
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

# **resolve_endpoint_resolve_post**
> ResolveResponse resolve_endpoint_resolve_post(body)

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
    api_response = api_instance.resolve_endpoint_resolve_post(body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningBoundaryApi->resolve_endpoint_resolve_post: %s\n" % e)
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

