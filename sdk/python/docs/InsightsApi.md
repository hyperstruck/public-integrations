# hyperstruck.InsightsApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_insight_endpoint_insights_post**](InsightsApi.md#create_insight_endpoint_insights_post) | **POST** /insights | Create an insight
[**delete_insight_endpoint_insights_insight_id_delete**](InsightsApi.md#delete_insight_endpoint_insights_insight_id_delete) | **DELETE** /insights/{insight_id} | Delete an insight and its runs and findings
[**get_insight_endpoint_insights_insight_id_get**](InsightsApi.md#get_insight_endpoint_insights_insight_id_get) | **GET** /insights/{insight_id} | Get an insight
[**list_findings_endpoint_insights_findings_get**](InsightsApi.md#list_findings_endpoint_insights_findings_get) | **GET** /insights/findings | List insight findings
[**list_insights_endpoint_insights_get**](InsightsApi.md#list_insights_endpoint_insights_get) | **GET** /insights | List insights
[**list_run_events_endpoint_insights_runs_run_id_events_get**](InsightsApi.md#list_run_events_endpoint_insights_runs_run_id_events_get) | **GET** /insights/runs/{run_id}/events | Poll an insight run&#x27;s events
[**list_runs_endpoint_insights_insight_id_runs_get**](InsightsApi.md#list_runs_endpoint_insights_insight_id_runs_get) | **GET** /insights/{insight_id}/runs | List an insight&#x27;s recent runs
[**refine_insight_endpoint_insights_refine_post**](InsightsApi.md#refine_insight_endpoint_insights_refine_post) | **POST** /insights/refine | Refine an insight draft
[**trigger_run_endpoint_insights_insight_id_runs_post**](InsightsApi.md#trigger_run_endpoint_insights_insight_id_runs_post) | **POST** /insights/{insight_id}/runs | Trigger an insight run
[**update_finding_endpoint_insights_findings_finding_id_patch**](InsightsApi.md#update_finding_endpoint_insights_findings_finding_id_patch) | **PATCH** /insights/findings/{finding_id} | Mark a finding actioned or dismissed
[**update_insight_endpoint_insights_insight_id_patch**](InsightsApi.md#update_insight_endpoint_insights_insight_id_patch) | **PATCH** /insights/{insight_id} | Update an insight

# **create_insight_endpoint_insights_post**
> InsightDefinitionResponse create_insight_endpoint_insights_post(body)

Create an insight

Create an insight rule. The caller must be able to read every agent it names.

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
api_instance = hyperstruck.InsightsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.InsightDefinitionCreateRequest() # InsightDefinitionCreateRequest |

try:
    # Create an insight
    api_response = api_instance.create_insight_endpoint_insights_post(body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling InsightsApi->create_insight_endpoint_insights_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**InsightDefinitionCreateRequest**](InsightDefinitionCreateRequest.md)|  |

### Return type

[**InsightDefinitionResponse**](InsightDefinitionResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **delete_insight_endpoint_insights_insight_id_delete**
> delete_insight_endpoint_insights_insight_id_delete(insight_id)

Delete an insight and its runs and findings

Same access as update: the rule's creator, or `can_write` on every agent it names or its runs consulted. Runs and findings are deleted with it; their usage records are kept for billing. 409 while a run of the rule is in progress.

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
api_instance = hyperstruck.InsightsApi(hyperstruck.ApiClient(configuration))
insight_id = NULL # object | Insight UUID returned by the insight create or list endpoint.

try:
    # Delete an insight and its runs and findings
    api_instance.delete_insight_endpoint_insights_insight_id_delete(insight_id)
except ApiException as e:
    print("Exception when calling InsightsApi->delete_insight_endpoint_insights_insight_id_delete: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **insight_id** | [**object**](.md)| Insight UUID returned by the insight create or list endpoint. |

### Return type

void (empty response body)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_insight_endpoint_insights_insight_id_get**
> InsightDefinitionResponse get_insight_endpoint_insights_insight_id_get(insight_id)

Get an insight

One insight rule with its latest run and open finding count. 404 unless the caller can read every agent it names.

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
api_instance = hyperstruck.InsightsApi(hyperstruck.ApiClient(configuration))
insight_id = NULL # object | Insight UUID returned by the insight create or list endpoint.

try:
    # Get an insight
    api_response = api_instance.get_insight_endpoint_insights_insight_id_get(insight_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling InsightsApi->get_insight_endpoint_insights_insight_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **insight_id** | [**object**](.md)| Insight UUID returned by the insight create or list endpoint. |

### Return type

[**InsightDefinitionResponse**](InsightDefinitionResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_findings_endpoint_insights_findings_get**
> InsightFindingListResponse list_findings_endpoint_insights_findings_get(insight_id=insight_id, run_id=run_id, status=status, limit=limit, cursor=cursor, include_held_drafts=include_held_drafts)

List insight findings

Findings across insights the caller can read, highest priority first.

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
api_instance = hyperstruck.InsightsApi(hyperstruck.ApiClient(configuration))
insight_id = NULL # object |  (optional)
run_id = NULL # object |  (optional)
status = NULL # object |  (optional)
limit = 50 # object |  (optional) (default to 50)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)
include_held_drafts = false # object |  (optional) (default to false)

try:
    # List insight findings
    api_response = api_instance.list_findings_endpoint_insights_findings_get(insight_id=insight_id, run_id=run_id, status=status, limit=limit, cursor=cursor, include_held_drafts=include_held_drafts)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling InsightsApi->list_findings_endpoint_insights_findings_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **insight_id** | [**object**](.md)|  | [optional]
 **run_id** | [**object**](.md)|  | [optional]
 **status** | [**object**](.md)|  | [optional]
 **limit** | [**object**](.md)|  | [optional] [default to 50]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]
 **include_held_drafts** | [**object**](.md)|  | [optional] [default to false]

### Return type

[**InsightFindingListResponse**](InsightFindingListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_insights_endpoint_insights_get**
> InsightDefinitionListResponse list_insights_endpoint_insights_get()

List insights

Insight rules whose agents the caller can all read.

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
api_instance = hyperstruck.InsightsApi(hyperstruck.ApiClient(configuration))

try:
    # List insights
    api_response = api_instance.list_insights_endpoint_insights_get()
    pprint(api_response)
except ApiException as e:
    print("Exception when calling InsightsApi->list_insights_endpoint_insights_get: %s\n" % e)
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**InsightDefinitionListResponse**](InsightDefinitionListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_run_events_endpoint_insights_runs_run_id_events_get**
> InsightRunEventsResponse list_run_events_endpoint_insights_runs_run_id_events_get(run_id, after_seq=after_seq)

Poll an insight run's events

Ordered step events after `after_seq`. The portal polls this to animate which agents are recalling, being asked, answering or being synthesized. `usage` is the run's own model spend (planning and synthesis, not the agents' answers), `pending` until the run finishes.

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
api_instance = hyperstruck.InsightsApi(hyperstruck.ApiClient(configuration))
run_id = NULL # object | Insight run UUID returned when a run is triggered.
after_seq = 0 # object |  (optional) (default to 0)

try:
    # Poll an insight run's events
    api_response = api_instance.list_run_events_endpoint_insights_runs_run_id_events_get(run_id, after_seq=after_seq)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling InsightsApi->list_run_events_endpoint_insights_runs_run_id_events_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **run_id** | [**object**](.md)| Insight run UUID returned when a run is triggered. |
 **after_seq** | [**object**](.md)|  | [optional] [default to 0]

### Return type

[**InsightRunEventsResponse**](InsightRunEventsResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_runs_endpoint_insights_insight_id_runs_get**
> InsightRunListResponse list_runs_endpoint_insights_insight_id_runs_get(insight_id, limit=limit)

List an insight's recent runs

Newest first. Only runs whose every consulted agent the caller can read are listed.

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
api_instance = hyperstruck.InsightsApi(hyperstruck.ApiClient(configuration))
insight_id = NULL # object | Insight UUID returned by the insight create or list endpoint.
limit = 20 # object |  (optional) (default to 20)

try:
    # List an insight's recent runs
    api_response = api_instance.list_runs_endpoint_insights_insight_id_runs_get(insight_id, limit=limit)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling InsightsApi->list_runs_endpoint_insights_insight_id_runs_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **insight_id** | [**object**](.md)| Insight UUID returned by the insight create or list endpoint. |
 **limit** | [**object**](.md)|  | [optional] [default to 20]

### Return type

[**InsightRunListResponse**](InsightRunListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **refine_insight_endpoint_insights_refine_post**
> InsightRefineResponse refine_insight_endpoint_insights_refine_post(body)

Refine an insight draft

Rewrite a draft objective into a specific, actionable insight and judge, from the selected agents' names and descriptions, whether they likely hold the data it needs. One small model call, held against the spend cap and billed when it succeeds; nothing is saved. 403 when any agent is unknown or unreadable, or (`reason` `spend_limit`) when the call would pass the spend cap.

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
api_instance = hyperstruck.InsightsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.InsightRefineRequest() # InsightRefineRequest |

try:
    # Refine an insight draft
    api_response = api_instance.refine_insight_endpoint_insights_refine_post(body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling InsightsApi->refine_insight_endpoint_insights_refine_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**InsightRefineRequest**](InsightRefineRequest.md)|  |

### Return type

[**InsightRefineResponse**](InsightRefineResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **trigger_run_endpoint_insights_insight_id_runs_post**
> InsightRunSummary trigger_run_endpoint_insights_insight_id_runs_post(insight_id)

Trigger an insight run

Start a run now: the orchestrator plans questions, asks each agent through its answer, learnings and obligations routes as the caller, and writes cited findings. Poll `/insights/runs/{run_id}/events`. The run's `trigger_kind` comes from how the request authenticated: `manual` for a portal session, `api` for an API key. A disabled insight only runs from the portal. The run's estimated model cost is held against the spend cap first: 403 (`reason` `spend_limit`) when it would pass the cap, before any agent or model is called.

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
api_instance = hyperstruck.InsightsApi(hyperstruck.ApiClient(configuration))
insight_id = NULL # object | Insight UUID returned by the insight create or list endpoint.

try:
    # Trigger an insight run
    api_response = api_instance.trigger_run_endpoint_insights_insight_id_runs_post(insight_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling InsightsApi->trigger_run_endpoint_insights_insight_id_runs_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **insight_id** | [**object**](.md)| Insight UUID returned by the insight create or list endpoint. |

### Return type

[**InsightRunSummary**](InsightRunSummary.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **update_finding_endpoint_insights_findings_finding_id_patch**
> InsightFindingResponse update_finding_endpoint_insights_findings_finding_id_patch(body, finding_id, include_held_drafts=include_held_drafts)

Mark a finding actioned or dismissed

Set a finding's status to `actioned` or `dismissed` (or back to `new`). The caller must be able to read every agent its insight names and its run consulted; otherwise 404.

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
api_instance = hyperstruck.InsightsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.InsightFindingUpdateRequest() # InsightFindingUpdateRequest |
finding_id = NULL # object | Insight finding UUID returned by the findings list.
include_held_drafts = false # object |  (optional) (default to false)

try:
    # Mark a finding actioned or dismissed
    api_response = api_instance.update_finding_endpoint_insights_findings_finding_id_patch(body, finding_id, include_held_drafts=include_held_drafts)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling InsightsApi->update_finding_endpoint_insights_findings_finding_id_patch: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**InsightFindingUpdateRequest**](InsightFindingUpdateRequest.md)|  |
 **finding_id** | [**object**](.md)| Insight finding UUID returned by the findings list. |
 **include_held_drafts** | [**object**](.md)|  | [optional] [default to false]

### Return type

[**InsightFindingResponse**](InsightFindingResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **update_insight_endpoint_insights_insight_id_patch**
> InsightDefinitionResponse update_insight_endpoint_insights_insight_id_patch(body, insight_id)

Update an insight

Needs `can_read` on every agent, plus being the rule's creator or having `can_write` on every agent it names or its runs consulted (403 otherwise).

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
api_instance = hyperstruck.InsightsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.InsightDefinitionUpdateRequest() # InsightDefinitionUpdateRequest |
insight_id = NULL # object | Insight UUID returned by the insight create or list endpoint.

try:
    # Update an insight
    api_response = api_instance.update_insight_endpoint_insights_insight_id_patch(body, insight_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling InsightsApi->update_insight_endpoint_insights_insight_id_patch: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**InsightDefinitionUpdateRequest**](InsightDefinitionUpdateRequest.md)|  |
 **insight_id** | [**object**](.md)| Insight UUID returned by the insight create or list endpoint. |

### Return type

[**InsightDefinitionResponse**](InsightDefinitionResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

