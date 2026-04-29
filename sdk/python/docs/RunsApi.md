# hyperstruck.RunsApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**dispatch_goal_run_endpoint_agents_agent_id_goals_post**](RunsApi.md#dispatch_goal_run_endpoint_agents_agent_id_goals_post) | **POST** /agents/{agent_id}/goals | Create Goal Run
[**get_run_endpoint_runs_run_id_get**](RunsApi.md#get_run_endpoint_runs_run_id_get) | **GET** /runs/{run_id} | Get Run
[**list_session_runs_endpoint_sessions_session_id_runs_get**](RunsApi.md#list_session_runs_endpoint_sessions_session_id_runs_get) | **GET** /sessions/{session_id}/runs | List Session Runs
[**resume_run_endpoint_runs_run_id_resume_post**](RunsApi.md#resume_run_endpoint_runs_run_id_resume_post) | **POST** /runs/{run_id}/resume | Resume Run

# **dispatch_goal_run_endpoint_agents_agent_id_goals_post**
> GoalRunAcceptedResponse dispatch_goal_run_endpoint_agents_agent_id_goals_post(body, agent_id)

Create Goal Run

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.RunsApi()
body = hyperstruck.GoalRunRequest() # GoalRunRequest | 
agent_id = NULL # object | 

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
 **agent_id** | [**object**](.md)|  | 

### Return type

[**GoalRunAcceptedResponse**](GoalRunAcceptedResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_run_endpoint_runs_run_id_get**
> RunResponse get_run_endpoint_runs_run_id_get(run_id)

Get Run

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.RunsApi()
run_id = NULL # object | 

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
 **run_id** | [**object**](.md)|  | 

### Return type

[**RunResponse**](RunResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_session_runs_endpoint_sessions_session_id_runs_get**
> RunListResponse list_session_runs_endpoint_sessions_session_id_runs_get(session_id, limit=limit, cursor=cursor)

List Session Runs

List runs in a session (newest first), keyset-paginated.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.RunsApi()
session_id = NULL # object | 
limit = 20 # object | Page size. (optional) (default to 20)
cursor = NULL # object | Opaque string from the previous page's `next_cursor`. (optional)

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
 **session_id** | [**object**](.md)|  | 
 **limit** | [**object**](.md)| Page size. | [optional] [default to 20]
 **cursor** | [**object**](.md)| Opaque string from the previous page&#x27;s &#x60;next_cursor&#x60;. | [optional] 

### Return type

[**RunListResponse**](RunListResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **resume_run_endpoint_runs_run_id_resume_post**
> GoalRunAcceptedResponse resume_run_endpoint_runs_run_id_resume_post(body, run_id)

Resume Run

Resume a suspended run with a human decision.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.RunsApi()
body = hyperstruck.ResumeRunRequest() # ResumeRunRequest | 
run_id = NULL # object | 

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
 **run_id** | [**object**](.md)|  | 

### Return type

[**GoalRunAcceptedResponse**](GoalRunAcceptedResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

