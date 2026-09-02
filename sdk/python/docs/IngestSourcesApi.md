# hyperstruck.IngestSourcesApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**compile_ingest_source_agents_agent_id_ingest_sources_compile_post**](IngestSourcesApi.md#compile_ingest_source_agents_agent_id_ingest_sources_compile_post) | **POST** /agents/{agent_id}/ingest-sources:compile | Preview a compiled URI watch
[**create_ingest_source_agents_agent_id_ingest_sources_post**](IngestSourcesApi.md#create_ingest_source_agents_agent_id_ingest_sources_post) | **POST** /agents/{agent_id}/ingest-sources | Save a URI watch
[**delete_ingest_source_agents_agent_id_ingest_sources_source_id_delete**](IngestSourcesApi.md#delete_ingest_source_agents_agent_id_ingest_sources_source_id_delete) | **DELETE** /agents/{agent_id}/ingest-sources/{source_id} | Remove a URI watch
[**get_ingest_source_runs_agents_agent_id_ingest_sources_source_id_runs_get**](IngestSourcesApi.md#get_ingest_source_runs_agents_agent_id_ingest_sources_source_id_runs_get) | **GET** /agents/{agent_id}/ingest-sources/{source_id}/runs | List URI watch runs
[**get_ingest_sources_agents_agent_id_ingest_sources_get**](IngestSourcesApi.md#get_ingest_sources_agents_agent_id_ingest_sources_get) | **GET** /agents/{agent_id}/ingest-sources | List URI watches
[**run_ingest_source_now_agents_agent_id_ingest_sources_source_id_run_now_post**](IngestSourcesApi.md#run_ingest_source_now_agents_agent_id_ingest_sources_source_id_run_now_post) | **POST** /agents/{agent_id}/ingest-sources/{source_id}/run-now | Enqueue a URI watch run
[**stop_ingest_source_agents_agent_id_ingest_sources_source_id_stop_post**](IngestSourcesApi.md#stop_ingest_source_agents_agent_id_ingest_sources_source_id_stop_post) | **POST** /agents/{agent_id}/ingest-sources/{source_id}/stop | Stop a live URI watch run
[**update_ingest_source_agents_agent_id_ingest_sources_source_id_patch**](IngestSourcesApi.md#update_ingest_source_agents_agent_id_ingest_sources_source_id_patch) | **PATCH** /agents/{agent_id}/ingest-sources/{source_id} | Update a URI watch

# **compile_ingest_source_agents_agent_id_ingest_sources_compile_post**
> CompileIngestSourceResponse compile_ingest_source_agents_agent_id_ingest_sources_compile_post(body, agent_id)

Preview a compiled URI watch

Compile a seed URL, cadence, and collection note into a reviewable spec. Does not save the watch and does not start a run. Cadence must be one of 15m, 1h, 6h, daily, or weekly.

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
api_instance = hyperstruck.IngestSourcesApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.CompileIngestSourceRequest() # CompileIngestSourceRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.

try:
    # Preview a compiled URI watch
    api_response = api_instance.compile_ingest_source_agents_agent_id_ingest_sources_compile_post(body, agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling IngestSourcesApi->compile_ingest_source_agents_agent_id_ingest_sources_compile_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**CompileIngestSourceRequest**](CompileIngestSourceRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

[**CompileIngestSourceResponse**](CompileIngestSourceResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **create_ingest_source_agents_agent_id_ingest_sources_post**
> IngestSourceResponse create_ingest_source_agents_agent_id_ingest_sources_post(body, agent_id)

Save a URI watch

Save a watch from the seed URL, cadence, collection note, page limit, and robots setting. The server compiles the crawl spec. Cadence cannot be faster than 15 minutes.

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
api_instance = hyperstruck.IngestSourcesApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.SaveIngestSourceRequest() # SaveIngestSourceRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.

try:
    # Save a URI watch
    api_response = api_instance.create_ingest_source_agents_agent_id_ingest_sources_post(body, agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling IngestSourcesApi->create_ingest_source_agents_agent_id_ingest_sources_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**SaveIngestSourceRequest**](SaveIngestSourceRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

[**IngestSourceResponse**](IngestSourceResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **delete_ingest_source_agents_agent_id_ingest_sources_source_id_delete**
> delete_ingest_source_agents_agent_id_ingest_sources_source_id_delete(agent_id, source_id)

Remove a URI watch

Stop scheduling the watch and cancel any live run. Already-uploaded documents stay. The same URI can be watched again after this.

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
api_instance = hyperstruck.IngestSourcesApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
source_id = NULL # object | Watch identifier returned when the URI source was saved. An admitted-source slug, never the URL.

try:
    # Remove a URI watch
    api_instance.delete_ingest_source_agents_agent_id_ingest_sources_source_id_delete(agent_id, source_id)
except ApiException as e:
    print("Exception when calling IngestSourcesApi->delete_ingest_source_agents_agent_id_ingest_sources_source_id_delete: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **source_id** | [**object**](.md)| Watch identifier returned when the URI source was saved. An admitted-source slug, never the URL. |

### Return type

void (empty response body)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_ingest_source_runs_agents_agent_id_ingest_sources_source_id_runs_get**
> IngestRunListResponse get_ingest_source_runs_agents_agent_id_ingest_sources_source_id_runs_get(agent_id, source_id)

List URI watch runs

Return recent runs for one watch, newest first.

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
api_instance = hyperstruck.IngestSourcesApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
source_id = NULL # object | Watch identifier returned when the URI source was saved. An admitted-source slug, never the URL.

try:
    # List URI watch runs
    api_response = api_instance.get_ingest_source_runs_agents_agent_id_ingest_sources_source_id_runs_get(agent_id, source_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling IngestSourcesApi->get_ingest_source_runs_agents_agent_id_ingest_sources_source_id_runs_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **source_id** | [**object**](.md)| Watch identifier returned when the URI source was saved. An admitted-source slug, never the URL. |

### Return type

[**IngestRunListResponse**](IngestRunListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_ingest_sources_agents_agent_id_ingest_sources_get**
> IngestSourceListResponse get_ingest_sources_agents_agent_id_ingest_sources_get(agent_id)

List URI watches

List saved watches for the agent, excluding cancelled sources.

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
api_instance = hyperstruck.IngestSourcesApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.

try:
    # List URI watches
    api_response = api_instance.get_ingest_sources_agents_agent_id_ingest_sources_get(agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling IngestSourcesApi->get_ingest_sources_agents_agent_id_ingest_sources_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

[**IngestSourceListResponse**](IngestSourceListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **run_ingest_source_now_agents_agent_id_ingest_sources_source_id_run_now_post**
> IngestRunAccepted run_ingest_source_now_agents_agent_id_ingest_sources_source_id_run_now_post(agent_id, source_id)

Enqueue a URI watch run

Queue an immediate run. Returns 202 accepted. The response is not proof the pages are searchable yet.

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
api_instance = hyperstruck.IngestSourcesApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
source_id = NULL # object | Watch identifier returned when the URI source was saved. An admitted-source slug, never the URL.

try:
    # Enqueue a URI watch run
    api_response = api_instance.run_ingest_source_now_agents_agent_id_ingest_sources_source_id_run_now_post(agent_id, source_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling IngestSourcesApi->run_ingest_source_now_agents_agent_id_ingest_sources_source_id_run_now_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **source_id** | [**object**](.md)| Watch identifier returned when the URI source was saved. An admitted-source slug, never the URL. |

### Return type

[**IngestRunAccepted**](IngestRunAccepted.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **stop_ingest_source_agents_agent_id_ingest_sources_source_id_stop_post**
> stop_ingest_source_agents_agent_id_ingest_sources_source_id_stop_post(agent_id, source_id)

Stop a live URI watch run

Cancel the live run. Processing runs settle the spend hold as used; pending runs release it. The watch stays active so Run now can start a new job. Idempotent when nothing is running.

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
api_instance = hyperstruck.IngestSourcesApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
source_id = NULL # object | Watch identifier returned when the URI source was saved. An admitted-source slug, never the URL.

try:
    # Stop a live URI watch run
    api_instance.stop_ingest_source_agents_agent_id_ingest_sources_source_id_stop_post(agent_id, source_id)
except ApiException as e:
    print("Exception when calling IngestSourcesApi->stop_ingest_source_agents_agent_id_ingest_sources_source_id_stop_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **source_id** | [**object**](.md)| Watch identifier returned when the URI source was saved. An admitted-source slug, never the URL. |

### Return type

void (empty response body)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **update_ingest_source_agents_agent_id_ingest_sources_source_id_patch**
> IngestSourceResponse update_ingest_source_agents_agent_id_ingest_sources_source_id_patch(body, agent_id, source_id)

Update a URI watch

Change cadence, pause or resume, page limit, robots setting, or the collection note. The server recompiles the crawl spec when those fields change.

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
api_instance = hyperstruck.IngestSourcesApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.PatchIngestSourceRequest() # PatchIngestSourceRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
source_id = NULL # object | Watch identifier returned when the URI source was saved. An admitted-source slug, never the URL.

try:
    # Update a URI watch
    api_response = api_instance.update_ingest_source_agents_agent_id_ingest_sources_source_id_patch(body, agent_id, source_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling IngestSourcesApi->update_ingest_source_agents_agent_id_ingest_sources_source_id_patch: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**PatchIngestSourceRequest**](PatchIngestSourceRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **source_id** | [**object**](.md)| Watch identifier returned when the URI source was saved. An admitted-source slug, never the URL. |

### Return type

[**IngestSourceResponse**](IngestSourceResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

