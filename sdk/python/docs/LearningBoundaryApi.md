# hyperstruck.LearningBoundaryApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**decline_endpoint_decline_post**](LearningBoundaryApi.md#decline_endpoint_decline_post) | **POST** /decline | Close a run whose turn had nothing worth learning
[**distill_endpoint_distill_post**](LearningBoundaryApi.md#distill_endpoint_distill_post) | **POST** /distill | Distill learnings from a corpus of evidence
[**funnel_endpoint_funnel_get**](LearningBoundaryApi.md#funnel_endpoint_funnel_get) | **GET** /funnel | Per-host loop-closure funnel
[**observe_endpoint_observe_post**](LearningBoundaryApi.md#observe_endpoint_observe_post) | **POST** /observe | Observe a finished episode
[**reinforce_endpoint_reinforce_post**](LearningBoundaryApi.md#reinforce_endpoint_reinforce_post) | **POST** /reinforce | Reinforce the learnings a run used
[**resolve_endpoint_resolve_post**](LearningBoundaryApi.md#resolve_endpoint_resolve_post) | **POST** /resolve | Resolve the learnings bound to a goal
[**run_status_endpoint_learning_runs_run_id_status_get**](LearningBoundaryApi.md#run_status_endpoint_learning_runs_run_id_status_get) | **GET** /learning-runs/{run_id}/status | What one run produced, per shelf

# **decline_endpoint_decline_post**
> BoundaryAcceptedResponse decline_endpoint_decline_post(body)

Close a run whose turn had nothing worth learning

Close a run the caller resolved but will not write back for, because the turn ended with nothing worth learning from. Supply ``agent_name`` (your agent's human-readable name, not the hosted UUID from `/agents/{agent_id}`). If no agent with that name exists yet, one is created automatically on first use within your tenant. Creating a new name requires `agents:write`. Use this instead of going silent: an unclosed run is indistinguishable from a host that stopped writing back, and only the caller knows which it is. Nothing is added to the corpus. Set `is_delivered` when the recall reached the model this turn, so the resolve is billed for what was received and released otherwise. A `run_id` this agent never resolved is accepted and ignored.

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
api_instance = hyperstruck.LearningBoundaryApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.DeclineRequest() # DeclineRequest |

try:
    # Close a run whose turn had nothing worth learning
    api_response = api_instance.decline_endpoint_decline_post(body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningBoundaryApi->decline_endpoint_decline_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**DeclineRequest**](DeclineRequest.md)|  |

### Return type

[**BoundaryAcceptedResponse**](BoundaryAcceptedResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **distill_endpoint_distill_post**
> BoundaryAcceptedResponse distill_endpoint_distill_post(body)

Distill learnings from a corpus of evidence

Distill durable learnings from post-mortems, documents, diffs, or analysis without inventing tool steps. Supply ``agent_name`` (your agent's human-readable name, not the hosted UUID from `/agents/{agent_id}`). If no agent with that name exists yet, one is created automatically on first use within your tenant. Creating a new name requires `agents:write`. Submit between 1 and 50 evidence items. A corpus that declares no contrast is accepted rather than refused: contrast is what the learning extractor compares against, so a corpus without it can still be full of facts, and a run that yields nothing for that reason comes back as `zero_reason: weak_contrast` on `GET /learning-runs/{run_id}/status`, where a count stays null until the job finishes, which is not the same as zero. `run_id` is a caller-created idempotency and tracing value, must begin with `distill:`, and does not reference `GET /runs/{run_id}`. A valid request may yield no learning. Pre-redact secrets from evidence.

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
api_instance = hyperstruck.LearningBoundaryApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.DistillRequest() # DistillRequest |

try:
    # Distill learnings from a corpus of evidence
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

[BearerApiKey](../README.md#BearerApiKey)

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

# Configure API key authorization: BearerApiKey
configuration = hyperstruck.Configuration()
configuration.api_key['Authorization'] = 'YOUR_API_KEY'
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['Authorization'] = 'Bearer'

# create an instance of the API class
api_instance = hyperstruck.LearningBoundaryApi(hyperstruck.ApiClient(configuration))
window_hours = 24 # object | Recent lookback window in hours. Must be at least 2 times `grace_minutes`, since a shorter window holds no run old enough to have closed; a request that is not is refused rather than answered. Narrowed to the reinforced-retention interval when it exceeds it, because past that boundary closed runs have been reclaimed while unclosed ones survive; the response reports the window actually used, and reports rates as null when that narrowing leaves the window below the same ratio. (optional) (default to 24)
grace_minutes = 120 # object | Minutes allowed for asynchronous write-back before a resolved run is counted as half-open. The default covers the 95th percentile of observed close times, so a run still legitimately in flight is reported as in-flight rather than as a non-closure. Bounded above by `window_hours`, per the ratio described there. (optional) (default to 120)

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
 **window_hours** | [**object**](.md)| Recent lookback window in hours. Must be at least 2 times &#x60;grace_minutes&#x60;, since a shorter window holds no run old enough to have closed; a request that is not is refused rather than answered. Narrowed to the reinforced-retention interval when it exceeds it, because past that boundary closed runs have been reclaimed while unclosed ones survive; the response reports the window actually used, and reports rates as null when that narrowing leaves the window below the same ratio. | [optional] [default to 24]
 **grace_minutes** | [**object**](.md)| Minutes allowed for asynchronous write-back before a resolved run is counted as half-open. The default covers the 95th percentile of observed close times, so a run still legitimately in flight is reported as in-flight rather than as a non-closure. Bounded above by &#x60;window_hours&#x60;, per the ratio described there. | [optional] [default to 120]

### Return type

[**LoopClosureFunnelResponse**](LoopClosureFunnelResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **observe_endpoint_observe_post**
> BoundaryAcceptedResponse observe_endpoint_observe_post(body)

Observe a finished episode

Submit a completed episode for asynchronous learning extraction. Supply ``agent_name`` (your agent's human-readable name, not the hosted UUID from `/agents/{agent_id}`). If no agent with that name exists yet, one is created automatically on first use within your tenant. Creating a new name requires `agents:write`. Direct API callers may construct the episode themselves; LangGraph is not required. Use a meaningful execution trace rather than documents or invented tool steps—use `/distill` for corpus evidence. The caller-owned episode `run_id` is an idempotency and correlation key, not a hosted run UUID.

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
api_instance = hyperstruck.LearningBoundaryApi(hyperstruck.ApiClient(configuration))
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

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **reinforce_endpoint_reinforce_post**
> BoundaryAcceptedResponse reinforce_endpoint_reinforce_post(body)

Reinforce the learnings a run used

Submit the completed outcome used to credit or correct learnings previously offered by resolve. Supply ``agent_name`` (your agent's human-readable name, not the hosted UUID from `/agents/{agent_id}`). If no agent with that name exists yet, one is created automatically on first use within your tenant. Creating a new name requires `agents:write`. Reuse the same caller-owned `run_id`; it is an idempotency and attribution key, not a hosted run UUID. Processing is asynchronous and the endpoint returns 202 when accepted.

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
api_instance = hyperstruck.LearningBoundaryApi(hyperstruck.ApiClient(configuration))
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

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **resolve_endpoint_resolve_post**
> ResolveResponse resolve_endpoint_resolve_post(body)

Resolve the learnings bound to a goal

Retrieve relevant learnings before external work begins. Supply ``agent_name`` (your agent's human-readable name, not the hosted UUID from `/agents/{agent_id}`). An existing name is looked up with `agents:read`. If the name does not exist yet, the caller must also hold `agents:write` or the request is refused with 403; a read-only key cannot mint agents. `run_id` is a caller-created correlation identifier, not a hosted run UUID. Reuse the same value with observe and reinforce so feedback can be attributed to the learnings offered here.

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
api_instance = hyperstruck.LearningBoundaryApi(hyperstruck.ApiClient(configuration))
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

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **run_status_endpoint_learning_runs_run_id_status_get**
> RunStatusResponse run_status_endpoint_learning_runs_run_id_status_get(run_id)

What one run produced, per shelf

Report a submitted run's state and, once it has finished, what it wrote to each shelf: learnings, claims, and the reason a count came back zero. A count is null while the run is unfinished, which is not the same as zero. An unknown run id, and a run another tenant owns, both answer 404.

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
api_instance = hyperstruck.LearningBoundaryApi(hyperstruck.ApiClient(configuration))
run_id = NULL # object | The run identifier you submitted the job under, exactly as sent. Scoped to your own tenant.

try:
    # What one run produced, per shelf
    api_response = api_instance.run_status_endpoint_learning_runs_run_id_status_get(run_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningBoundaryApi->run_status_endpoint_learning_runs_run_id_status_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **run_id** | [**object**](.md)| The run identifier you submitted the job under, exactly as sent. Scoped to your own tenant. |

### Return type

[**RunStatusResponse**](RunStatusResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

