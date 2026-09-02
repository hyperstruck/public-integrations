# hyperstruck.AgentValueApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_value_profile_endpoint_agents_agent_id_value_profile_get**](AgentValueApi.md#get_value_profile_endpoint_agents_agent_id_value_profile_get) | **GET** /agents/{agent_id}/value-profile | Get Agent Value Profile
[**get_value_summary_endpoint_agents_agent_id_value_get**](AgentValueApi.md#get_value_summary_endpoint_agents_agent_id_value_get) | **GET** /agents/{agent_id}/value | Get Agent Lifetime Value
[**list_value_events_endpoint_agents_agent_id_value_events_get**](AgentValueApi.md#list_value_events_endpoint_agents_agent_id_value_events_get) | **GET** /agents/{agent_id}/value-events | List Agent Value Entries
[**put_value_profile_endpoint_agents_agent_id_value_profile_put**](AgentValueApi.md#put_value_profile_endpoint_agents_agent_id_value_profile_put) | **PUT** /agents/{agent_id}/value-profile | Set Agent Value Profile
[**record_value_event_endpoint_agents_agent_id_value_events_post**](AgentValueApi.md#record_value_event_endpoint_agents_agent_id_value_events_post) | **POST** /agents/{agent_id}/value-events | Record Agent Value
[**reverse_value_event_endpoint_agents_agent_id_value_events_event_id_reversal_post**](AgentValueApi.md#reverse_value_event_endpoint_agents_agent_id_value_events_event_id_reversal_post) | **POST** /agents/{agent_id}/value-events/{event_id}/reversal | Reverse Agent Value

# **get_value_profile_endpoint_agents_agent_id_value_profile_get**
> AgentValueProfile get_value_profile_endpoint_agents_agent_id_value_profile_get(agent_id)

Get Agent Value Profile

Read whether lifetime value is tracked for this agent, what counts as value, its rate card and rates. `guidance` says, in plain language, how to record value for this agent. Read it before recording value. An agent with no saved profile returns the defaults with tracking off.

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
api_instance = hyperstruck.AgentValueApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.

try:
    # Get Agent Value Profile
    api_response = api_instance.get_value_profile_endpoint_agents_agent_id_value_profile_get(agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AgentValueApi->get_value_profile_endpoint_agents_agent_id_value_profile_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

[**AgentValueProfile**](AgentValueProfile.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_value_summary_endpoint_agents_agent_id_value_get**
> AgentValueSummary get_value_summary_endpoint_agents_agent_id_value_get(agent_id, window=window)

Get Agent Lifetime Value

Lifetime value for one agent: measured and estimated dollars (always reported apart), time saved, value by category and by rate-card unit, and the learnings that earned the most. Use it to judge whether an agent pays for itself, or to pick between agents.

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
api_instance = hyperstruck.AgentValueApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
window = hyperstruck.ValueWindow() # ValueWindow | How far back to count. Defaults to the agent's lifetime. (optional) (default to all_time)

try:
    # Get Agent Lifetime Value
    api_response = api_instance.get_value_summary_endpoint_agents_agent_id_value_get(agent_id, window=window)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AgentValueApi->get_value_summary_endpoint_agents_agent_id_value_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **window** | [**ValueWindow**](.md)| How far back to count. Defaults to the agent&#x27;s lifetime. | [optional] [default to all_time]

### Return type

[**AgentValueSummary**](AgentValueSummary.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_value_events_endpoint_agents_agent_id_value_events_get**
> ValueEventPage list_value_events_endpoint_agents_agent_id_value_events_get(agent_id, kind=kind, limit=limit, cursor=cursor)

List Agent Value Entries

The agent's value ledger, newest first, with who recorded each entry and how its amount was worked out. Each item carries its `idempotency_key`, so a caller that replayed a key can find the entry it wrote.

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
api_instance = hyperstruck.AgentValueApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
kind = NULL # object | Only measured, or only estimated, entries. (optional)
limit = 25 # object | Maximum number of items to return on this page. (optional) (default to 25)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)

try:
    # List Agent Value Entries
    api_response = api_instance.list_value_events_endpoint_agents_agent_id_value_events_get(agent_id, kind=kind, limit=limit, cursor=cursor)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AgentValueApi->list_value_events_endpoint_agents_agent_id_value_events_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **kind** | [**object**](.md)| Only measured, or only estimated, entries. | [optional]
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 25]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]

### Return type

[**ValueEventPage**](ValueEventPage.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **put_value_profile_endpoint_agents_agent_id_value_profile_put**
> AgentValueProfile put_value_profile_endpoint_agents_agent_id_value_profile_put(body, agent_id)

Set Agent Value Profile

Turn lifetime value tracking on or off and set what counts as value: a plain-language description, the hourly rate that turns minutes into dollars, the platform estimate, and a rate card of named, priced units. Replaces the whole profile. Editing prices never changes entries already recorded.

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
api_instance = hyperstruck.AgentValueApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.AgentValueProfileUpdate() # AgentValueProfileUpdate |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.

try:
    # Set Agent Value Profile
    api_response = api_instance.put_value_profile_endpoint_agents_agent_id_value_profile_put(body, agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AgentValueApi->put_value_profile_endpoint_agents_agent_id_value_profile_put: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**AgentValueProfileUpdate**](AgentValueProfileUpdate.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

[**AgentValueProfile**](AgentValueProfile.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **record_value_event_endpoint_agents_agent_id_value_events_post**
> record_value_event_endpoint_agents_agent_id_value_events_post(body, agent_id)

Record Agent Value

Record value this agent produced, as one append-only ledger entry. Send exactly one figure: `unit_key` and `quantity` from the agent's rate card (preferred: the price is already agreed), `amount_usd` with a `baseline`, or `time_saved_minutes` alone. Pass `run_id` to credit the learnings and claims that run was offered. Record value only when this agent's value tracking is on and you have a basis you did not invent: a rate-card unit that matches what happened, or a figure a person, a document or a system of record stated. Never guess a dollar figure; the platform writes its own estimate after successful runs. Read the value profile's `guidance` first.

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
api_instance = hyperstruck.AgentValueApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.ValueEventCreate() # ValueEventCreate |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.

try:
    # Record Agent Value
    api_instance.record_value_event_endpoint_agents_agent_id_value_events_post(body, agent_id)
except ApiException as e:
    print("Exception when calling AgentValueApi->record_value_event_endpoint_agents_agent_id_value_events_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ValueEventCreate**](ValueEventCreate.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

void (empty response body)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **reverse_value_event_endpoint_agents_agent_id_value_events_event_id_reversal_post**
> reverse_value_event_endpoint_agents_agent_id_value_events_event_id_reversal_post(body, agent_id, event_id)

Reverse Agent Value

Cancel a ledger entry that turned out wrong (the placement fell through, the bounty was withdrawn). Writes a negating entry with your reason, dated with the original so both fall in the same summary window; the original stays visible. Each entry can be reversed once; retrying with the same reason returns that reversal.

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
api_instance = hyperstruck.AgentValueApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.ValueReversalRequest() # ValueReversalRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
event_id = NULL # object | Value entry id from the ledger or a record response.

try:
    # Reverse Agent Value
    api_instance.reverse_value_event_endpoint_agents_agent_id_value_events_event_id_reversal_post(body, agent_id, event_id)
except ApiException as e:
    print("Exception when calling AgentValueApi->reverse_value_event_endpoint_agents_agent_id_value_events_event_id_reversal_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ValueReversalRequest**](ValueReversalRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **event_id** | [**object**](.md)| Value entry id from the ledger or a record response. |

### Return type

void (empty response body)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

