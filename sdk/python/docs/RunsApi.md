# hyperstruck.RunsApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**dispatch_goal_run_endpoint_agents_agent_id_goals_post**](RunsApi.md#dispatch_goal_run_endpoint_agents_agent_id_goals_post) | **POST** /agents/{agent_id}/goals | Create Goal Run
[**get_run_endpoint_runs_run_id_get**](RunsApi.md#get_run_endpoint_runs_run_id_get) | **GET** /runs/{run_id} | Get Run
[**list_agent_runs_endpoint_agents_agent_id_runs_get**](RunsApi.md#list_agent_runs_endpoint_agents_agent_id_runs_get) | **GET** /agents/{agent_id}/runs | List Agent Runs
[**list_session_runs_endpoint_sessions_session_id_runs_get**](RunsApi.md#list_session_runs_endpoint_sessions_session_id_runs_get) | **GET** /sessions/{session_id}/runs | List Session Runs
[**resume_run_endpoint_runs_run_id_resume_post**](RunsApi.md#resume_run_endpoint_runs_run_id_resume_post) | **POST** /runs/{run_id}/resume | Resume Run

# **dispatch_goal_run_endpoint_agents_agent_id_goals_post**
> GoalRunAcceptedResponse dispatch_goal_run_endpoint_agents_agent_id_goals_post(body, agent_id)

Create Goal Run

Start asynchronous work for a hosted agent. A 202 response contains the server-issued run UUID; use `GET /runs/{run_id}` to follow its status and resume it if human input is requested.

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
api_instance = hyperstruck.RunsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.GoalRunRequest() # GoalRunRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.

try:
    # Create Goal Run
    api_response = api_instance.dispatch_goal_run_endpoint_agents_agent_id_goals_post(body, agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling RunsApi->dispatch_goal_run_endpoint_agents_agent_id_goals_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**GoalRunRequest**](GoalRunRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

[**GoalRunAcceptedResponse**](GoalRunAcceptedResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_run_endpoint_runs_run_id_get**
> RunDetailResponse get_run_endpoint_runs_run_id_get(run_id)

Get Run

Retrieve the latest state and result of a hosted run by its server-issued UUID. Poll this endpoint after starting or resuming a run until it reaches a terminal state or requests human input.

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
api_instance = hyperstruck.RunsApi(hyperstruck.ApiClient(configuration))
run_id = NULL # object | Server-issued hosted run UUID returned when a run is accepted.

try:
    # Get Run
    api_response = api_instance.get_run_endpoint_runs_run_id_get(run_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling RunsApi->get_run_endpoint_runs_run_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **run_id** | [**object**](.md)| Server-issued hosted run UUID returned when a run is accepted. |

### Return type

[**RunDetailResponse**](RunDetailResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_agent_runs_endpoint_agents_agent_id_runs_get**
> AgentRunListResponse list_agent_runs_endpoint_agents_agent_id_runs_get(agent_id, status=status, run_type=run_type, session_id=session_id, window=window, limit=limit, cursor=cursor)

List Agent Runs

List hosted runs for one agent, optionally filtered by status, type, session, or reporting window. Use the returned run UUIDs with `/runs`.

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
api_instance = hyperstruck.RunsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
status = [] # object | Filter by one or more run statuses. (optional) (default to [])
run_type = [] # object | Filter by one or more run types (goal|resume). (optional) (default to [])
session_id = NULL # object | Filter to a single session. (optional)
window = hyperstruck.UsageTimeWindow() # UsageTimeWindow | Window bounding which runs are returned. (optional) (default to last_30_days)
limit = 25 # object | Maximum number of items to return on this page. (optional) (default to 25)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)

try:
    # List Agent Runs
    api_response = api_instance.list_agent_runs_endpoint_agents_agent_id_runs_get(agent_id, status=status, run_type=run_type, session_id=session_id, window=window, limit=limit, cursor=cursor)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling RunsApi->list_agent_runs_endpoint_agents_agent_id_runs_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **status** | [**object**](.md)| Filter by one or more run statuses. | [optional] [default to []]
 **run_type** | [**object**](.md)| Filter by one or more run types (goal|resume). | [optional] [default to []]
 **session_id** | [**object**](.md)| Filter to a single session. | [optional]
 **window** | [**UsageTimeWindow**](.md)| Window bounding which runs are returned. | [optional] [default to last_30_days]
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 25]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]

### Return type

[**AgentRunListResponse**](AgentRunListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_session_runs_endpoint_sessions_session_id_runs_get**
> RunListResponse list_session_runs_endpoint_sessions_session_id_runs_get(session_id, limit=limit, cursor=cursor)

List Session Runs

List the hosted runs associated with one conversation session, newest first. Use the returned run UUIDs to inspect individual run details.

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
api_instance = hyperstruck.RunsApi(hyperstruck.ApiClient(configuration))
session_id = NULL # object | Conversation session UUID associated with an agent.
limit = 20 # object | Maximum number of items to return on this page. (optional) (default to 20)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)

try:
    # List Session Runs
    api_response = api_instance.list_session_runs_endpoint_sessions_session_id_runs_get(session_id, limit=limit, cursor=cursor)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling RunsApi->list_session_runs_endpoint_sessions_session_id_runs_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **session_id** | [**object**](.md)| Conversation session UUID associated with an agent. |
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 20]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]

### Return type

[**RunListResponse**](RunListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **resume_run_endpoint_runs_run_id_resume_post**
> GoalRunAcceptedResponse resume_run_endpoint_runs_run_id_resume_post(body, run_id)

Resume Run

Continue a suspended hosted run with the requested human decision. A 202 response contains the accepted child run; follow it with `GET /runs/{run_id}`.

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
api_instance = hyperstruck.RunsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.ResumeRunRequest() # ResumeRunRequest |
run_id = NULL # object | Server-issued hosted run UUID returned when a run is accepted.

try:
    # Resume Run
    api_response = api_instance.resume_run_endpoint_runs_run_id_resume_post(body, run_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling RunsApi->resume_run_endpoint_runs_run_id_resume_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ResumeRunRequest**](ResumeRunRequest.md)|  |
 **run_id** | [**object**](.md)| Server-issued hosted run UUID returned when a run is accepted. |

### Return type

[**GoalRunAcceptedResponse**](GoalRunAcceptedResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

