# hyperstruck.LearningsApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**delete_agent_learnings_endpoint_agents_agent_id_learnings_delete**](LearningsApi.md#delete_agent_learnings_endpoint_agents_agent_id_learnings_delete) | **DELETE** /agents/{agent_id}/learnings | Delete all learnings for an agent
[**get_learning_endpoint_agents_agent_id_learnings_learning_id_get**](LearningsApi.md#get_learning_endpoint_agents_agent_id_learnings_learning_id_get) | **GET** /agents/{agent_id}/learnings/{learning_id} | Get a learning
[**reinforce_learning_endpoint_agents_agent_id_learnings_learning_id_reinforce_post**](LearningsApi.md#reinforce_learning_endpoint_agents_agent_id_learnings_learning_id_reinforce_post) | **POST** /agents/{agent_id}/learnings/{learning_id}/reinforce | Reinforce a learning
[**search_learnings_endpoint_agents_agent_id_learnings_search_get**](LearningsApi.md#search_learnings_endpoint_agents_agent_id_learnings_search_get) | **GET** /agents/{agent_id}/learnings/search | Search learnings
[**store_learning_endpoint_agents_agent_id_learnings_post**](LearningsApi.md#store_learning_endpoint_agents_agent_id_learnings_post) | **POST** /agents/{agent_id}/learnings | Store a learning

# **delete_agent_learnings_endpoint_agents_agent_id_learnings_delete**
> DeleteLearningsResponse delete_agent_learnings_endpoint_agents_agent_id_learnings_delete(agent_id)

Delete all learnings for an agent

Delete every learning memory scoped to the agent. This is a destructive operation and does not affect other memory categories.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.LearningsApi()
agent_id = NULL # object | 

try:
    # Delete all learnings for an agent
    api_response = api_instance.delete_agent_learnings_endpoint_agents_agent_id_learnings_delete(agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningsApi->delete_agent_learnings_endpoint_agents_agent_id_learnings_delete: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)|  | 

### Return type

[**DeleteLearningsResponse**](DeleteLearningsResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_learning_endpoint_agents_agent_id_learnings_learning_id_get**
> LearningResponse get_learning_endpoint_agents_agent_id_learnings_learning_id_get(agent_id, learning_id)

Get a learning

Retrieve a single learning by its ID.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.LearningsApi()
agent_id = NULL # object | 
learning_id = NULL # object | 

try:
    # Get a learning
    api_response = api_instance.get_learning_endpoint_agents_agent_id_learnings_learning_id_get(agent_id, learning_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningsApi->get_learning_endpoint_agents_agent_id_learnings_learning_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)|  | 
 **learning_id** | [**object**](.md)|  | 

### Return type

[**LearningResponse**](LearningResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **reinforce_learning_endpoint_agents_agent_id_learnings_learning_id_reinforce_post**
> ReinforceLearningResponse reinforce_learning_endpoint_agents_agent_id_learnings_learning_id_reinforce_post(body, agent_id, learning_id)

Reinforce a learning

Provide feedback on whether a learning was helpful. Updates the learning's confidence and trust level based on the feedback signal.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.LearningsApi()
body = hyperstruck.ReinforceLearningRequest() # ReinforceLearningRequest | 
agent_id = NULL # object | 
learning_id = NULL # object | 

try:
    # Reinforce a learning
    api_response = api_instance.reinforce_learning_endpoint_agents_agent_id_learnings_learning_id_reinforce_post(body, agent_id, learning_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningsApi->reinforce_learning_endpoint_agents_agent_id_learnings_learning_id_reinforce_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ReinforceLearningRequest**](ReinforceLearningRequest.md)|  | 
 **agent_id** | [**object**](.md)|  | 
 **learning_id** | [**object**](.md)|  | 

### Return type

[**ReinforceLearningResponse**](ReinforceLearningResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **search_learnings_endpoint_agents_agent_id_learnings_search_get**
> LearningSearchResponse search_learnings_endpoint_agents_agent_id_learnings_search_get(agent_id, q, limit=limit, min_confidence=min_confidence, scope=scope)

Search learnings

Semantic search over the agent's learning memories. Results are ranked intelligently by relevance, considering decay of older learnings and diversity filtering to avoid redundant results.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.LearningsApi()
agent_id = NULL # object | 
q = NULL # object | Search query text.
limit = 10 # object | Maximum number of results to return. (optional) (default to 10)
min_confidence = NULL # object | Minimum confidence threshold for results. (optional)
scope = hyperstruck.LearningScope() # LearningScope | Search scope. 'agent' searches the agent's private learnings. 'org' searches shared learnings across agents (Enterprise only). (optional) (default to agent)

try:
    # Search learnings
    api_response = api_instance.search_learnings_endpoint_agents_agent_id_learnings_search_get(agent_id, q, limit=limit, min_confidence=min_confidence, scope=scope)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningsApi->search_learnings_endpoint_agents_agent_id_learnings_search_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)|  | 
 **q** | [**object**](.md)| Search query text. | 
 **limit** | [**object**](.md)| Maximum number of results to return. | [optional] [default to 10]
 **min_confidence** | [**object**](.md)| Minimum confidence threshold for results. | [optional] 
 **scope** | [**LearningScope**](.md)| Search scope. &#x27;agent&#x27; searches the agent&#x27;s private learnings. &#x27;org&#x27; searches shared learnings across agents (Enterprise only). | [optional] [default to agent]

### Return type

[**LearningSearchResponse**](LearningSearchResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **store_learning_endpoint_agents_agent_id_learnings_post**
> StoreLearningAcceptedResponse store_learning_endpoint_agents_agent_id_learnings_post(body, agent_id)

Store a learning

Store a new learning for the agent. The learning is processed through the platform's deduplication and conflict prevention pipeline on a background worker so the request returns immediately.

### Example
```python
from __future__ import print_function
import time
import hyperstruck
from hyperstruck.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = hyperstruck.LearningsApi()
body = hyperstruck.StoreLearningRequest() # StoreLearningRequest | 
agent_id = NULL # object | 

try:
    # Store a learning
    api_response = api_instance.store_learning_endpoint_agents_agent_id_learnings_post(body, agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling LearningsApi->store_learning_endpoint_agents_agent_id_learnings_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**StoreLearningRequest**](StoreLearningRequest.md)|  | 
 **agent_id** | [**object**](.md)|  | 

### Return type

[**StoreLearningAcceptedResponse**](StoreLearningAcceptedResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

