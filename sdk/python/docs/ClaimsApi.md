# hyperstruck.ClaimsApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**alias_endpoint_agents_agent_id_entities_entity_id_aliases_post**](ClaimsApi.md#alias_endpoint_agents_agent_id_entities_entity_id_aliases_post) | **POST** /agents/{agent_id}/entities/{entity_id}/aliases | Name an entity
[**attributes_endpoint_agents_agent_id_attributes_get**](ClaimsApi.md#attributes_endpoint_agents_agent_id_attributes_get) | **GET** /agents/{agent_id}/attributes | List the attributes
[**claim_documents_endpoint_agents_agent_id_claim_documents_get**](ClaimsApi.md#claim_documents_endpoint_agents_agent_id_claim_documents_get) | **GET** /agents/{agent_id}/claim-documents | Recent documents that changed something
[**correct_endpoint_agents_agent_id_statements_post**](ClaimsApi.md#correct_endpoint_agents_agent_id_statements_post) | **POST** /agents/{agent_id}/statements | Correct a claim
[**entity_changes_endpoint_agents_agent_id_entities_entity_id_changes_get**](ClaimsApi.md#entity_changes_endpoint_agents_agent_id_entities_entity_id_changes_get) | **GET** /agents/{agent_id}/entities/{entity_id}/changes | What changed on an entity between two dates
[**entity_dossier_endpoint_agents_agent_id_entities_entity_id_dossier_get**](ClaimsApi.md#entity_dossier_endpoint_agents_agent_id_entities_entity_id_dossier_get) | **GET** /agents/{agent_id}/entities/{entity_id}/dossier | Get an entity&#x27;s dossier
[**entity_sources_endpoint_agents_agent_id_entities_entity_id_sources_get**](ClaimsApi.md#entity_sources_endpoint_agents_agent_id_entities_entity_id_sources_get) | **GET** /agents/{agent_id}/entities/{entity_id}/sources | Where an entity&#x27;s claims came from
[**erase_entity_endpoint_agents_agent_id_entities_entity_id_erasure_post**](ClaimsApi.md#erase_entity_endpoint_agents_agent_id_entities_entity_id_erasure_post) | **POST** /agents/{agent_id}/entities/{entity_id}/erasure | Erase an entity and its claims
[**find_entities_endpoint_agents_agent_id_entities_get**](ClaimsApi.md#find_entities_endpoint_agents_agent_id_entities_get) | **GET** /agents/{agent_id}/entities | Find or list an agent&#x27;s entities
[**fold_endpoint_agents_agent_id_attributes_attribute_id_fold_post**](ClaimsApi.md#fold_endpoint_agents_agent_id_attributes_attribute_id_fold_post) | **POST** /agents/{agent_id}/attributes/{attribute_id}/fold | Fold an attribute onto another
[**list_agent_claims_endpoint_agents_agent_id_claims_get**](ClaimsApi.md#list_agent_claims_endpoint_agents_agent_id_claims_get) | **GET** /agents/{agent_id}/claims | List an agent&#x27;s claims
[**merge_endpoint_agents_agent_id_entities_entity_id_merge_post**](ClaimsApi.md#merge_endpoint_agents_agent_id_entities_entity_id_merge_post) | **POST** /agents/{agent_id}/entities/{entity_id}/merge | Merge an entity into another
[**nature_endpoint_agents_agent_id_attributes_attribute_id_nature_post**](ClaimsApi.md#nature_endpoint_agents_agent_id_attributes_attribute_id_nature_post) | **POST** /agents/{agent_id}/attributes/{attribute_id}/nature | Set an attribute&#x27;s nature or protection
[**search_claims_endpoint_agents_agent_id_claims_search_post**](ClaimsApi.md#search_claims_endpoint_agents_agent_id_claims_search_post) | **POST** /agents/{agent_id}/claims/search | Search the agent&#x27;s claims
[**settle_endpoint_agents_agent_id_verdicts_post**](ClaimsApi.md#settle_endpoint_agents_agent_id_verdicts_post) | **POST** /agents/{agent_id}/verdicts | Settle a conflict
[**split_endpoint_agents_agent_id_entities_entity_id_split_post**](ClaimsApi.md#split_endpoint_agents_agent_id_entities_entity_id_split_post) | **POST** /agents/{agent_id}/entities/{entity_id}/split | Split two entities apart
[**to_decide_endpoint_agents_agent_id_to_decide_get**](ClaimsApi.md#to_decide_endpoint_agents_agent_id_to_decide_get) | **GET** /agents/{agent_id}/to-decide | What is left to decide
[**wipe_agent_claims_endpoint_agents_agent_id_claims_delete**](ClaimsApi.md#wipe_agent_claims_endpoint_agents_agent_id_claims_delete) | **DELETE** /agents/{agent_id}/claims | Erase a batch of this agent&#x27;s entities and their claims

# **alias_endpoint_agents_agent_id_entities_entity_id_aliases_post**
> AliasOut alias_endpoint_agents_agent_id_entities_entity_id_aliases_post(body, agent_id, entity_id)

Name an entity

A person says what else the entity is called; answers with the entity and every alias it has.

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
api_instance = hyperstruck.ClaimsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.AliasIn() # AliasIn |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
entity_id = NULL # object | Claim entity UUID (the unit of identity and of erasure).

try:
    # Name an entity
    api_response = api_instance.alias_endpoint_agents_agent_id_entities_entity_id_aliases_post(body, agent_id, entity_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->alias_endpoint_agents_agent_id_entities_entity_id_aliases_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**AliasIn**](AliasIn.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **entity_id** | [**object**](.md)| Claim entity UUID (the unit of identity and of erasure). |

### Return type

[**AliasOut**](AliasOut.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **attributes_endpoint_agents_agent_id_attributes_get**
> AttributesPage attributes_endpoint_agents_agent_id_attributes_get(agent_id, q=q, kind=kind, cursor=cursor, limit=limit)

List the attributes

The agent's attributes in name order, folded ones included, with the nature and protection each carries.

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
api_instance = hyperstruck.ClaimsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
q = NULL # object | A name containing this. (optional)
kind = NULL # object | The attribute's kind. (optional)
cursor = NULL # object | Opaque page cursor: pass a response's `cursor` back verbatim. Its encoding is not part of the contract. (optional)
limit = 50 # object |  (optional) (default to 50)

try:
    # List the attributes
    api_response = api_instance.attributes_endpoint_agents_agent_id_attributes_get(agent_id, q=q, kind=kind, cursor=cursor, limit=limit)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->attributes_endpoint_agents_agent_id_attributes_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **q** | [**object**](.md)| A name containing this. | [optional]
 **kind** | [**object**](.md)| The attribute&#x27;s kind. | [optional]
 **cursor** | [**object**](.md)| Opaque page cursor: pass a response&#x27;s &#x60;cursor&#x60; back verbatim. Its encoding is not part of the contract. | [optional]
 **limit** | [**object**](.md)|  | [optional] [default to 50]

### Return type

[**AttributesPage**](AttributesPage.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **claim_documents_endpoint_agents_agent_id_claim_documents_get**
> ClaimDocumentsPage claim_documents_endpoint_agents_agent_id_claim_documents_get(agent_id, scope=scope, raised_after=raised_after, document=document, cursor=cursor, limit=limit, reveal=reveal)

Recent documents that changed something

The documents the claim store holds that changed something, newest first by document date: notes, runs and people's corrections. Each says how many keys it established (its statement is the current one), ended (it replaced an earlier one) and left to decide (a side of a conflict cites it), with the first three of each as Claim items at `detail=full`. A document that changed nothing is not listed. Answers 409 `claims_not_replayed` until the agent's claims have been rebuilt.

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
api_instance = hyperstruck.ClaimsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
scope = NULL # object | Only documents that changed this entity or one standing relation from it. (optional)
raised_after = NULL # object | Only documents dated at or after this, with an offset. (optional)
document = NULL # object | Only this document, by its id or by the Documents tab's id for it. (optional)
cursor = NULL # object | Opaque page cursor: pass a response's `cursor` back verbatim. Its encoding is not part of the contract. (optional)
limit = 50 # object |  (optional) (default to 50)
reveal = false # object | Show the protected values a read otherwise withholds (a bank account number reads `Ends 5560`). Only a caller holding `claims:curate` who also has the right to change the agent may ask; anyone else is refused with 403 `curate_required`. (optional) (default to false)

try:
    # Recent documents that changed something
    api_response = api_instance.claim_documents_endpoint_agents_agent_id_claim_documents_get(agent_id, scope=scope, raised_after=raised_after, document=document, cursor=cursor, limit=limit, reveal=reveal)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->claim_documents_endpoint_agents_agent_id_claim_documents_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **scope** | [**object**](.md)| Only documents that changed this entity or one standing relation from it. | [optional]
 **raised_after** | [**object**](.md)| Only documents dated at or after this, with an offset. | [optional]
 **document** | [**object**](.md)| Only this document, by its id or by the Documents tab&#x27;s id for it. | [optional]
 **cursor** | [**object**](.md)| Opaque page cursor: pass a response&#x27;s &#x60;cursor&#x60; back verbatim. Its encoding is not part of the contract. | [optional]
 **limit** | [**object**](.md)|  | [optional] [default to 50]
 **reveal** | [**object**](.md)| Show the protected values a read otherwise withholds (a bank account number reads &#x60;Ends 5560&#x60;). Only a caller holding &#x60;claims:curate&#x60; who also has the right to change the agent may ask; anyone else is refused with 403 &#x60;curate_required&#x60;. | [optional] [default to false]

### Return type

[**ClaimDocumentsPage**](ClaimDocumentsPage.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **correct_endpoint_agents_agent_id_statements_post**
> CorrectOut correct_endpoint_agents_agent_id_statements_post(body, agent_id)

Correct a claim

Says what is now so. With `replaces` (a statement the caller was shown) the key is that claim's and unsent fields are carried from it; without, `entity_id`, `attribute_id` and `value` are required. Answers with the statement that now stands and the Claim item of its key. A retry with the same `request_id` writes nothing and answers with the same ids.

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
api_instance = hyperstruck.ClaimsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.CorrectIn() # CorrectIn |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.

try:
    # Correct a claim
    api_response = api_instance.correct_endpoint_agents_agent_id_statements_post(body, agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->correct_endpoint_agents_agent_id_statements_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**CorrectIn**](CorrectIn.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

[**CorrectOut**](CorrectOut.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **entity_changes_endpoint_agents_agent_id_entities_entity_id_changes_get**
> ChangesOut entity_changes_endpoint_agents_agent_id_entities_entity_id_changes_get(agent_id, entity_id, since, until=until, cursor=cursor, limit=limit, reveal=reveal)

What changed on an entity between two dates

Each key on the entity whose claim changed between `since` and `until`, newest change first, with the statement it held before (`from`) and after (`to`). Pages like the claims list: pass `cursor` back with the same `since` and `until`. Answers 404 when the entity is not held here.

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
api_instance = hyperstruck.ClaimsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
entity_id = NULL # object | Claim entity UUID (the unit of identity and of erasure).
since = NULL # object | With an offset (`2026-09-01T00:00:00Z`).
until = NULL # object | With an offset. Defaults to now. (optional)
cursor = NULL # object | Opaque page cursor: pass a response's `cursor` back verbatim. Its encoding is not part of the contract. (optional)
limit = 50 # object |  (optional) (default to 50)
reveal = false # object | Show the protected values a read otherwise withholds (a bank account number reads `Ends 5560`). Only a caller holding `claims:curate` who also has the right to change the agent may ask; anyone else is refused with 403 `curate_required`. (optional) (default to false)

try:
    # What changed on an entity between two dates
    api_response = api_instance.entity_changes_endpoint_agents_agent_id_entities_entity_id_changes_get(agent_id, entity_id, since, until=until, cursor=cursor, limit=limit, reveal=reveal)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->entity_changes_endpoint_agents_agent_id_entities_entity_id_changes_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **entity_id** | [**object**](.md)| Claim entity UUID (the unit of identity and of erasure). |
 **since** | [**object**](.md)| With an offset (&#x60;2026-09-01T00:00:00Z&#x60;). |
 **until** | [**object**](.md)| With an offset. Defaults to now. | [optional]
 **cursor** | [**object**](.md)| Opaque page cursor: pass a response&#x27;s &#x60;cursor&#x60; back verbatim. Its encoding is not part of the contract. | [optional]
 **limit** | [**object**](.md)|  | [optional] [default to 50]
 **reveal** | [**object**](.md)| Show the protected values a read otherwise withholds (a bank account number reads &#x60;Ends 5560&#x60;). Only a caller holding &#x60;claims:curate&#x60; who also has the right to change the agent may ask; anyone else is refused with 403 &#x60;curate_required&#x60;. | [optional] [default to false]

### Return type

[**ChangesOut**](ChangesOut.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **entity_dossier_endpoint_agents_agent_id_entities_entity_id_dossier_get**
> EntityDossierOut entity_dossier_endpoint_agents_agent_id_entities_entity_id_dossier_get(agent_id, entity_id, detail=detail, cursor=cursor, limit=limit, reveal=reveal)

Get an entity's dossier

Everything the account holds about one entity: its claims page by page, and on the first page its relations and the obligations it owes, the newest few of each (`more` says when there are others, and where to list them). `detail=cited` adds each claim's other live statements and source excerpts; `detail=full` adds the statements each one replaced. Answers 404 when the entity is not held here.

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
api_instance = hyperstruck.ClaimsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
entity_id = NULL # object | Claim entity UUID (the unit of identity and of erasure).
detail = concise # object |  (optional) (default to concise)
cursor = NULL # object | Opaque page cursor: pass a response's `cursor` back verbatim. Its encoding is not part of the contract. (optional)
limit = 50 # object |  (optional) (default to 50)
reveal = false # object | Show the protected values a read otherwise withholds (a bank account number reads `Ends 5560`). Only a caller holding `claims:curate` who also has the right to change the agent may ask; anyone else is refused with 403 `curate_required`. (optional) (default to false)

try:
    # Get an entity's dossier
    api_response = api_instance.entity_dossier_endpoint_agents_agent_id_entities_entity_id_dossier_get(agent_id, entity_id, detail=detail, cursor=cursor, limit=limit, reveal=reveal)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->entity_dossier_endpoint_agents_agent_id_entities_entity_id_dossier_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **entity_id** | [**object**](.md)| Claim entity UUID (the unit of identity and of erasure). |
 **detail** | [**object**](.md)|  | [optional] [default to concise]
 **cursor** | [**object**](.md)| Opaque page cursor: pass a response&#x27;s &#x60;cursor&#x60; back verbatim. Its encoding is not part of the contract. | [optional]
 **limit** | [**object**](.md)|  | [optional] [default to 50]
 **reveal** | [**object**](.md)| Show the protected values a read otherwise withholds (a bank account number reads &#x60;Ends 5560&#x60;). Only a caller holding &#x60;claims:curate&#x60; who also has the right to change the agent may ask; anyone else is refused with 403 &#x60;curate_required&#x60;. | [optional] [default to false]

### Return type

[**EntityDossierOut**](EntityDossierOut.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **entity_sources_endpoint_agents_agent_id_entities_entity_id_sources_get**
> SourcesPageOut entity_sources_endpoint_agents_agent_id_entities_entity_id_sources_get(agent_id, entity_id, key=key, cursor=cursor, limit=limit, reveal=reveal)

Where an entity's claims came from

The documents that gave claims about the entity, newest first, with the documents of one thread (a channel, an email thread) as a single row. Each row says its `channel`, how many documents and claims it covers and their first and latest dates; `total` counts the rows and `total_documents` the documents. `key` reads one row alone. A cursor from another entity answers 422 `invalid_cursor`. Answers 404 when the entity is not held here.

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
api_instance = hyperstruck.ClaimsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
entity_id = NULL # object | Claim entity UUID (the unit of identity and of erasure).
key = NULL # object |  (optional)
cursor = NULL # object | Opaque page cursor: pass a response's `cursor` back verbatim. Its encoding is not part of the contract. (optional)
limit = 50 # object |  (optional) (default to 50)
reveal = false # object | Show the protected values a read otherwise withholds (a bank account number reads `Ends 5560`). Only a caller holding `claims:curate` who also has the right to change the agent may ask; anyone else is refused with 403 `curate_required`. (optional) (default to false)

try:
    # Where an entity's claims came from
    api_response = api_instance.entity_sources_endpoint_agents_agent_id_entities_entity_id_sources_get(agent_id, entity_id, key=key, cursor=cursor, limit=limit, reveal=reveal)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->entity_sources_endpoint_agents_agent_id_entities_entity_id_sources_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **entity_id** | [**object**](.md)| Claim entity UUID (the unit of identity and of erasure). |
 **key** | [**object**](.md)|  | [optional]
 **cursor** | [**object**](.md)| Opaque page cursor: pass a response&#x27;s &#x60;cursor&#x60; back verbatim. Its encoding is not part of the contract. | [optional]
 **limit** | [**object**](.md)|  | [optional] [default to 50]
 **reveal** | [**object**](.md)| Show the protected values a read otherwise withholds (a bank account number reads &#x60;Ends 5560&#x60;). Only a caller holding &#x60;claims:curate&#x60; who also has the right to change the agent may ask; anyone else is refused with 403 &#x60;curate_required&#x60;. | [optional] [default to false]

### Return type

[**SourcesPageOut**](SourcesPageOut.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **erase_entity_endpoint_agents_agent_id_entities_entity_id_erasure_post**
> ErasureReceiptOut erase_entity_endpoint_agents_agent_id_entities_entity_id_erasure_post(agent_id, entity_id, dry_run=dry_run)

Erase an entity and its claims

Erases the entity, its claims, the verdicts naming them and its aliases, and returns the receipt. With `dry_run=true` the same statements run and are rolled back: the receipt is the one the erasure would give, nothing is written, and the same `can_administer` is needed.

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
api_instance = hyperstruck.ClaimsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
entity_id = NULL # object | Claim entity UUID (the unit of identity and of erasure).
dry_run = false # object | Return the receipt the erasure would give and write nothing. (optional) (default to false)

try:
    # Erase an entity and its claims
    api_response = api_instance.erase_entity_endpoint_agents_agent_id_entities_entity_id_erasure_post(agent_id, entity_id, dry_run=dry_run)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->erase_entity_endpoint_agents_agent_id_entities_entity_id_erasure_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **entity_id** | [**object**](.md)| Claim entity UUID (the unit of identity and of erasure). |
 **dry_run** | [**object**](.md)| Return the receipt the erasure would give and write nothing. | [optional] [default to false]

### Return type

[**ErasureReceiptOut**](ErasureReceiptOut.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **find_entities_endpoint_agents_agent_id_entities_get**
> EntityCandidates find_entities_endpoint_agents_agent_id_entities_get(agent_id, q=q, type=type, cursor=cursor, limit=limit, reveal=reveal)

Find or list an agent's entities

With `q`, the entities whose name or alias matches, best match first, each with its type and the newest relation that places it. Without `q`, every surviving entity the agent holds a live claim about: people, organizations, places, projects and records first, then every other type, each tier newest change first, with its `details` and `owed` counts and its newest change, cursor-paged, filtered by `type`, with `total` and `type_counts`; a cursor from another `type` filter answers 422 `invalid_cursor`.

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
api_instance = hyperstruck.ClaimsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
q = NULL # object |  (optional)
type = NULL # object | Listing only: keep these entity types. (optional)
cursor = NULL # object | Opaque page cursor: pass a response's `cursor` back verbatim. Its encoding is not part of the contract. (optional)
limit = 10 # object |  (optional) (default to 10)
reveal = false # object | Show the protected values a read otherwise withholds (a bank account number reads `Ends 5560`). Only a caller holding `claims:curate` who also has the right to change the agent may ask; anyone else is refused with 403 `curate_required`. (optional) (default to false)

try:
    # Find or list an agent's entities
    api_response = api_instance.find_entities_endpoint_agents_agent_id_entities_get(agent_id, q=q, type=type, cursor=cursor, limit=limit, reveal=reveal)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->find_entities_endpoint_agents_agent_id_entities_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **q** | [**object**](.md)|  | [optional]
 **type** | [**object**](.md)| Listing only: keep these entity types. | [optional]
 **cursor** | [**object**](.md)| Opaque page cursor: pass a response&#x27;s &#x60;cursor&#x60; back verbatim. Its encoding is not part of the contract. | [optional]
 **limit** | [**object**](.md)|  | [optional] [default to 10]
 **reveal** | [**object**](.md)| Show the protected values a read otherwise withholds (a bank account number reads &#x60;Ends 5560&#x60;). Only a caller holding &#x60;claims:curate&#x60; who also has the right to change the agent may ask; anyone else is refused with 403 &#x60;curate_required&#x60;. | [optional] [default to false]

### Return type

[**EntityCandidates**](EntityCandidates.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **fold_endpoint_agents_agent_id_attributes_attribute_id_fold_post**
> AttributeWriteOut fold_endpoint_agents_agent_id_attributes_attribute_id_fold_post(body, agent_id, attribute_id)

Fold an attribute onto another

A person says the attribute is a synonym of `into`; `fold_refused` names `into` and the reason.

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
api_instance = hyperstruck.ClaimsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.FoldIn() # FoldIn |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
attribute_id = NULL # object | Key (claim attribute) UUID: the registry id of a filing slot, as the keys-awaiting-review listing returns it.

try:
    # Fold an attribute onto another
    api_response = api_instance.fold_endpoint_agents_agent_id_attributes_attribute_id_fold_post(body, agent_id, attribute_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->fold_endpoint_agents_agent_id_attributes_attribute_id_fold_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**FoldIn**](FoldIn.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **attribute_id** | [**object**](.md)| Key (claim attribute) UUID: the registry id of a filing slot, as the keys-awaiting-review listing returns it. |

### Return type

[**AttributeWriteOut**](AttributeWriteOut.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_agent_claims_endpoint_agents_agent_id_claims_get**
> ClaimItemsPage list_agent_claims_endpoint_agents_agent_id_claims_get(agent_id, entity=entity, state=state, kind=kind, owner=owner, due_before=due_before, due_after=due_after, as_of=as_of, scope=scope, document=document, container=container, attribute=attribute, raised_after=raised_after, raised_before=raised_before, due=due, order=order, detail=detail, cursor=cursor, limit=limit, reveal=reveal)

List an agent's claims

One item per key (an entity, an attribute and its qualifiers), with the claim current on it and its state, and the `total` of keys the filter matches. Filters narrow by entity (or `scope`: the entity and everything one standing relation from it), state, kind, obligation holder and due date, the document or container a statement cites, fields, when the current statement was recorded, and whether an obligation has a date; `order` is `key` (default), `raised` (newest first) or `due` (soonest first, obligations only; `due_before` implies it). `as_of` reads the account as it stood then. A cursor is valid only with the order and filters it was handed out under, else 422 `invalid_cursor`. Answers 409 `claims_not_replayed` until the agent's claims have been rebuilt on the keyed store.

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
api_instance = hyperstruck.ClaimsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
entity = NULL # object | Only this entity's keys. (optional)
state = NULL # object | settled, unanswered, conflicting, open, done or ended. (optional)
kind = NULL # object | The attribute's kind. (optional)
owner = NULL # object | Obligations this entity holds. (optional)
due_before = NULL # object | Obligations due before this time, with an offset (`2026-09-01T00:00:00Z`). (optional)
due_after = NULL # object | Obligations due at or after this time, with an offset; ordered by due date like `due_before`. (optional)
as_of = NULL # object | Read the account as it stood then, with an offset (`2026-09-01T00:00:00Z`). (optional)
scope = NULL # object | This entity and every entity one standing relation from it, in either direction, as of `as_of`. (optional)
document = NULL # object | Only keys any of whose statements cite this document (the id a statement's `document` carries). (optional)
container = NULL # object | Only keys citing a document of this container (a thread or channel, as `container` on a source). (optional)
attribute = NULL # object | Only keys of these fields. (optional)
raised_after = NULL # object | Only keys whose current statement (for a conflict, its newer side) was recorded at or after this. (optional)
raised_before = NULL # object | Only keys whose current statement was recorded before this. (optional)
due = NULL # object | `dated` or `none`: obligations whose current statement has a due date, or lacks one. (optional)
order = NULL # object | `key` (default), `raised` (newest first) or `due` (soonest first; obligations only). (optional)
detail = concise # object |  (optional) (default to concise)
cursor = NULL # object | Opaque page cursor: pass a response's `cursor` back verbatim. Its encoding is not part of the contract. (optional)
limit = 50 # object |  (optional) (default to 50)
reveal = false # object | Show the protected values a read otherwise withholds (a bank account number reads `Ends 5560`). Only a caller holding `claims:curate` who also has the right to change the agent may ask; anyone else is refused with 403 `curate_required`. (optional) (default to false)

try:
    # List an agent's claims
    api_response = api_instance.list_agent_claims_endpoint_agents_agent_id_claims_get(agent_id, entity=entity, state=state, kind=kind, owner=owner, due_before=due_before, due_after=due_after, as_of=as_of, scope=scope, document=document, container=container, attribute=attribute, raised_after=raised_after, raised_before=raised_before, due=due, order=order, detail=detail, cursor=cursor, limit=limit, reveal=reveal)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->list_agent_claims_endpoint_agents_agent_id_claims_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **entity** | [**object**](.md)| Only this entity&#x27;s keys. | [optional]
 **state** | [**object**](.md)| settled, unanswered, conflicting, open, done or ended. | [optional]
 **kind** | [**object**](.md)| The attribute&#x27;s kind. | [optional]
 **owner** | [**object**](.md)| Obligations this entity holds. | [optional]
 **due_before** | [**object**](.md)| Obligations due before this time, with an offset (&#x60;2026-09-01T00:00:00Z&#x60;). | [optional]
 **due_after** | [**object**](.md)| Obligations due at or after this time, with an offset; ordered by due date like &#x60;due_before&#x60;. | [optional]
 **as_of** | [**object**](.md)| Read the account as it stood then, with an offset (&#x60;2026-09-01T00:00:00Z&#x60;). | [optional]
 **scope** | [**object**](.md)| This entity and every entity one standing relation from it, in either direction, as of &#x60;as_of&#x60;. | [optional]
 **document** | [**object**](.md)| Only keys any of whose statements cite this document (the id a statement&#x27;s &#x60;document&#x60; carries). | [optional]
 **container** | [**object**](.md)| Only keys citing a document of this container (a thread or channel, as &#x60;container&#x60; on a source). | [optional]
 **attribute** | [**object**](.md)| Only keys of these fields. | [optional]
 **raised_after** | [**object**](.md)| Only keys whose current statement (for a conflict, its newer side) was recorded at or after this. | [optional]
 **raised_before** | [**object**](.md)| Only keys whose current statement was recorded before this. | [optional]
 **due** | [**object**](.md)| &#x60;dated&#x60; or &#x60;none&#x60;: obligations whose current statement has a due date, or lacks one. | [optional]
 **order** | [**object**](.md)| &#x60;key&#x60; (default), &#x60;raised&#x60; (newest first) or &#x60;due&#x60; (soonest first; obligations only). | [optional]
 **detail** | [**object**](.md)|  | [optional] [default to concise]
 **cursor** | [**object**](.md)| Opaque page cursor: pass a response&#x27;s &#x60;cursor&#x60; back verbatim. Its encoding is not part of the contract. | [optional]
 **limit** | [**object**](.md)|  | [optional] [default to 50]
 **reveal** | [**object**](.md)| Show the protected values a read otherwise withholds (a bank account number reads &#x60;Ends 5560&#x60;). Only a caller holding &#x60;claims:curate&#x60; who also has the right to change the agent may ask; anyone else is refused with 403 &#x60;curate_required&#x60;. | [optional] [default to false]

### Return type

[**ClaimItemsPage**](ClaimItemsPage.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **merge_endpoint_agents_agent_id_entities_entity_id_merge_post**
> MergeOut merge_endpoint_agents_agent_id_entities_entity_id_merge_post(body, agent_id, entity_id)

Merge an entity into another

A person says the entity and `into` are one thing; answers with the entity that survives.

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
api_instance = hyperstruck.ClaimsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.MergeIn() # MergeIn |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
entity_id = NULL # object | Claim entity UUID (the unit of identity and of erasure).

try:
    # Merge an entity into another
    api_response = api_instance.merge_endpoint_agents_agent_id_entities_entity_id_merge_post(body, agent_id, entity_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->merge_endpoint_agents_agent_id_entities_entity_id_merge_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**MergeIn**](MergeIn.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **entity_id** | [**object**](.md)| Claim entity UUID (the unit of identity and of erasure). |

### Return type

[**MergeOut**](MergeOut.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **nature_endpoint_agents_agent_id_attributes_attribute_id_nature_post**
> AttributeWriteOut nature_endpoint_agents_agent_id_attributes_attribute_id_nature_post(body, agent_id, attribute_id)

Set an attribute's nature or protection

Unsent fields keep their value. A key with `claims:correct` may only raise `protected`; anything else from a key is `person_required`. Lowering a protection needs the right to change the agent (its steward, a manager, an org admin); a caller who may only curate is refused with 403 `agent_write_required`.

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
api_instance = hyperstruck.ClaimsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.NatureIn() # NatureIn |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
attribute_id = NULL # object | Key (claim attribute) UUID: the registry id of a filing slot, as the keys-awaiting-review listing returns it.

try:
    # Set an attribute's nature or protection
    api_response = api_instance.nature_endpoint_agents_agent_id_attributes_attribute_id_nature_post(body, agent_id, attribute_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->nature_endpoint_agents_agent_id_attributes_attribute_id_nature_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**NatureIn**](NatureIn.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **attribute_id** | [**object**](.md)| Key (claim attribute) UUID: the registry id of a filing slot, as the keys-awaiting-review listing returns it. |

### Return type

[**AttributeWriteOut**](AttributeWriteOut.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **search_claims_endpoint_agents_agent_id_claims_search_post**
> ClaimSearchOut search_claims_endpoint_agents_agent_id_claims_search_post(body, agent_id, reveal=reveal)

Search the agent's claims

Searches the agent's claims for the ones nearest the question and renders them by code under one line saying so, each paragraph opened by its entity and attribute, with the same claims beside the text as items, so the same question gets the same result. The claims are the nearest the account holds and may not answer the question; whether one answers is the caller's to judge. Compose from what is handed over first and narrow only after. `shares_no_word` is true when no claim shares a word with the question, so the claims are the nearest by meaning alone, and `more_matched` counts the claims the question's words matched beyond those handed over. Each item's `word_share` and `cosine` say how much of the question's words it carries and how near it is in meaning. Only an account or entity holding no live claim gets `shape: absent`. When the search by meaning is unavailable the result says `degraded: embedding_unavailable` or `degraded: vectors_loading` and ranks by words alone; `vectors_loading` is said only when an account's copies failed to load or were dropped as out of date. Each deploy empties the copies the search by meaning reads, so after a deploy an account's first question waits for its signs to load (about a second at 500,000 claims) and ranks by them until the numbers arrive (a few seconds more). `entity` narrows the search to one entity's claims (404 when the account does not hold it). With any of `state`, `kind`, `owner` or `due_before` the result is `shape: set`: the claims GET /claims would list for that filter, one row each under a line stating the filter, paged by `cursor` and `limit`; the question is not ranked. A safe read: nothing is written or billed, so a retry needs no Idempotency-Key. Returns 409 `claims_not_replayed` until the agent's claims have been rebuilt on the keyed store.

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
api_instance = hyperstruck.ClaimsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.ClaimSearchIn() # ClaimSearchIn |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
reveal = false # object | Show the protected values a read otherwise withholds (a bank account number reads `Ends 5560`). Only a caller holding `claims:curate` who also has the right to change the agent may ask; anyone else is refused with 403 `curate_required`. (optional) (default to false)

try:
    # Search the agent's claims
    api_response = api_instance.search_claims_endpoint_agents_agent_id_claims_search_post(body, agent_id, reveal=reveal)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->search_claims_endpoint_agents_agent_id_claims_search_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ClaimSearchIn**](ClaimSearchIn.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **reveal** | [**object**](.md)| Show the protected values a read otherwise withholds (a bank account number reads &#x60;Ends 5560&#x60;). Only a caller holding &#x60;claims:curate&#x60; who also has the right to change the agent may ask; anyone else is refused with 403 &#x60;curate_required&#x60;. | [optional] [default to false]

### Return type

[**ClaimSearchOut**](ClaimSearchOut.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **settle_endpoint_agents_agent_id_verdicts_post**
> SettleOut settle_endpoint_agents_agent_id_verdicts_post(body, agent_id)

Settle a conflict

Says which of the claims a conflict is about stands (`stands`), or that both do (`both`). `statement_id` is a statement the caller was shown, `current.id` or a `beside[].id` of a conflicting Claim item. Answers with the verdicts written and the Claim item of every key the settle touched. A retry with the same `request_id` writes nothing and answers with the same ids.

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
api_instance = hyperstruck.ClaimsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.SettleIn() # SettleIn |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.

try:
    # Settle a conflict
    api_response = api_instance.settle_endpoint_agents_agent_id_verdicts_post(body, agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->settle_endpoint_agents_agent_id_verdicts_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**SettleIn**](SettleIn.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

[**SettleOut**](SettleOut.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **split_endpoint_agents_agent_id_entities_entity_id_split_post**
> SplitOut split_endpoint_agents_agent_id_entities_entity_id_split_post(body, agent_id, entity_id)

Split two entities apart

A person says the entity and `from` are not one thing; without `from` the merge the entity sits behind is undone. Answers with the entities now apart. `split_not_adjacent` names `from` and the path between them.

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
api_instance = hyperstruck.ClaimsApi(hyperstruck.ApiClient(configuration))
body = hyperstruck.SplitIn() # SplitIn |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
entity_id = NULL # object | Claim entity UUID (the unit of identity and of erasure).

try:
    # Split two entities apart
    api_response = api_instance.split_endpoint_agents_agent_id_entities_entity_id_split_post(body, agent_id, entity_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->split_endpoint_agents_agent_id_entities_entity_id_split_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**SplitIn**](SplitIn.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **entity_id** | [**object**](.md)| Claim entity UUID (the unit of identity and of erasure). |

### Return type

[**SplitOut**](SplitOut.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **to_decide_endpoint_agents_agent_id_to_decide_get**
> ToDecidePage to_decide_endpoint_agents_agent_id_to_decide_get(agent_id, kind=kind, scope=scope, entity=entity, raised_after=raised_after, order=order, group=group, cursor=cursor, limit=limit, reveal=reveal)

What is left to decide

The agent's conflicts and open possible duplicates in one list, ordered by when each was raised (`newest` by default), a page at a time with the `total`. A conflict is the same item `GET /claims?state=conflicting` returns; a possible duplicate names both entities (each as its surviving entity), the `rule` that raised it and a `reason_sentence`. A pair whose sides are now one entity is left out. With `group` the list is ordered by group then by raised date and `groups` counts each group across the whole filter. A cursor is valid only with the order, group and filters it was handed out under, else 422 `invalid_cursor`. Answers 409 `claims_not_replayed` until the agent's claims have been rebuilt.

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
api_instance = hyperstruck.ClaimsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
kind = NULL # object | `conflict` or `duplicate`. (optional)
scope = NULL # object | This entity and every entity one standing relation from it. (optional)
entity = NULL # object | Only this entity's own decisions, not its neighbours'. (optional)
raised_after = NULL # object | Only decisions raised at or after this, with an offset. (optional)
order = newest # object |  (optional) (default to newest)
group = none # object |  (optional) (default to none)
cursor = NULL # object | Opaque page cursor: pass a response's `cursor` back verbatim. Its encoding is not part of the contract. (optional)
limit = 50 # object |  (optional) (default to 50)
reveal = false # object | Show the protected values a read otherwise withholds (a bank account number reads `Ends 5560`). Only a caller holding `claims:curate` who also has the right to change the agent may ask; anyone else is refused with 403 `curate_required`. (optional) (default to false)

try:
    # What is left to decide
    api_response = api_instance.to_decide_endpoint_agents_agent_id_to_decide_get(agent_id, kind=kind, scope=scope, entity=entity, raised_after=raised_after, order=order, group=group, cursor=cursor, limit=limit, reveal=reveal)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->to_decide_endpoint_agents_agent_id_to_decide_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **kind** | [**object**](.md)| &#x60;conflict&#x60; or &#x60;duplicate&#x60;. | [optional]
 **scope** | [**object**](.md)| This entity and every entity one standing relation from it. | [optional]
 **entity** | [**object**](.md)| Only this entity&#x27;s own decisions, not its neighbours&#x27;. | [optional]
 **raised_after** | [**object**](.md)| Only decisions raised at or after this, with an offset. | [optional]
 **order** | [**object**](.md)|  | [optional] [default to newest]
 **group** | [**object**](.md)|  | [optional] [default to none]
 **cursor** | [**object**](.md)| Opaque page cursor: pass a response&#x27;s &#x60;cursor&#x60; back verbatim. Its encoding is not part of the contract. | [optional]
 **limit** | [**object**](.md)|  | [optional] [default to 50]
 **reveal** | [**object**](.md)| Show the protected values a read otherwise withholds (a bank account number reads &#x60;Ends 5560&#x60;). Only a caller holding &#x60;claims:curate&#x60; who also has the right to change the agent may ask; anyone else is refused with 403 &#x60;curate_required&#x60;. | [optional] [default to false]

### Return type

[**ToDecidePage**](ToDecidePage.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **wipe_agent_claims_endpoint_agents_agent_id_claims_delete**
> ClaimWipeResponse wipe_agent_claims_endpoint_agents_agent_id_claims_delete(agent_id, body=body)

Erase a batch of this agent's entities and their claims

Empties the agent's keyed claim store in one pass, so nothing remains afterwards.

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
api_instance = hyperstruck.ClaimsApi(hyperstruck.ApiClient(configuration))
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
body = NULL # object |  (optional)

try:
    # Erase a batch of this agent's entities and their claims
    api_response = api_instance.wipe_agent_claims_endpoint_agents_agent_id_claims_delete(agent_id, body=body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->wipe_agent_claims_endpoint_agents_agent_id_claims_delete: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **body** | [**object**](object.md)|  | [optional]

### Return type

[**ClaimWipeResponse**](ClaimWipeResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

