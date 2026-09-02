# hyperstruck.PlansApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**search_agent_similar_plans_endpoint_agents_agent_id_plans_similar_get**](PlansApi.md#search_agent_similar_plans_endpoint_agents_agent_id_plans_similar_get) | **GET** /agents/{agent_id}/plans/similar | Search similar plans for one agent
[**search_multi_agent_similar_plans_endpoint_plans_similar_post**](PlansApi.md#search_multi_agent_similar_plans_endpoint_plans_similar_post) | **POST** /plans/similar | Search similar plans across multiple agents

# **search_agent_similar_plans_endpoint_agents_agent_id_plans_similar_get**
> SimilarPlansResponse search_agent_similar_plans_endpoint_agents_agent_id_plans_similar_get(agent_id, q, limit=limit)

Search similar plans for one agent

Search one agent's prior plans for approaches relevant to a new goal. Use this read-only endpoint when planning should benefit from that agent's previous experience.

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
api_instance = hyperstruck.PlansApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
q = NULL # object | Search query text used to retrieve similar plans.
limit = NULL # object | Optional max results; capped at 10 per agent. (optional)

try:
    # Search similar plans for one agent
    api_response = api_instance.search_agent_similar_plans_endpoint_agents_agent_id_plans_similar_get(agent_id, q, limit=limit)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling PlansApi->search_agent_similar_plans_endpoint_agents_agent_id_plans_similar_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **q** | [**object**](.md)| Search query text used to retrieve similar plans. |
 **limit** | [**object**](.md)| Optional max results; capped at 10 per agent. | [optional]

### Return type

[**SimilarPlansResponse**](SimilarPlansResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **search_multi_agent_similar_plans_endpoint_plans_similar_post**
> SimilarPlansResponse search_multi_agent_similar_plans_endpoint_plans_similar_post(body)

Search similar plans across multiple agents

Search prior plans across several accessible agents in one request. Use this for coordination or routing when experience may be distributed across agents.

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
api_instance = hyperstruck.PlansApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.MultiAgentPlanSearchRequest() # MultiAgentPlanSearchRequest |

try:
    # Search similar plans across multiple agents
    api_response = api_instance.search_multi_agent_similar_plans_endpoint_plans_similar_post(body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling PlansApi->search_multi_agent_similar_plans_endpoint_plans_similar_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**MultiAgentPlanSearchRequest**](MultiAgentPlanSearchRequest.md)|  |

### Return type

[**SimilarPlansResponse**](SimilarPlansResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

