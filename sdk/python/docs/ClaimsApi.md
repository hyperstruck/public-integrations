# hyperstruck.ClaimsApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**admin_release_claim_endpoint_agents_agent_id_claims_claim_id_admin_release_post**](ClaimsApi.md#admin_release_claim_endpoint_agents_agent_id_claims_claim_id_admin_release_post) | **POST** /agents/{agent_id}/claims/{claim_id}/admin-release | Release a quarantined claim (administrator path)
[**adopt_claim_endpoint_agents_agent_id_claims_claim_id_adopt_post**](ClaimsApi.md#adopt_claim_endpoint_agents_agent_id_claims_claim_id_adopt_post) | **POST** /agents/{agent_id}/claims/{claim_id}/adopt | Adopt an abstained claim under a structural attribute
[**create_alias_endpoint_agents_agent_id_claims_entities_entity_id_aliases_post**](ClaimsApi.md#create_alias_endpoint_agents_agent_id_claims_entities_entity_id_aliases_post) | **POST** /agents/{agent_id}/claims/entities/{entity_id}/aliases | Author an alias for an entity
[**deactivate_alias_endpoint_agents_agent_id_claims_aliases_alias_id_deactivate_post**](ClaimsApi.md#deactivate_alias_endpoint_agents_agent_id_claims_aliases_alias_id_deactivate_post) | **POST** /agents/{agent_id}/claims/aliases/{alias_id}/deactivate | Deactivate an alias
[**erase_entity_endpoint_agents_agent_id_claims_entities_entity_id_erasure_post**](ClaimsApi.md#erase_entity_endpoint_agents_agent_id_claims_entities_entity_id_erasure_post) | **POST** /agents/{agent_id}/claims/entities/{entity_id}/erasure | Erase an entity&#x27;s claim layer
[**get_attribute_endpoint_agents_agent_id_claims_attributes_attribute_id_get**](ClaimsApi.md#get_attribute_endpoint_agents_agent_id_claims_attributes_attribute_id_get) | **GET** /agents/{agent_id}/claims/attributes/{attribute_id} | Resolve a claim attribute registry id
[**get_entity_dossier_endpoint_agents_agent_id_claims_entities_entity_id_get**](ClaimsApi.md#get_entity_dossier_endpoint_agents_agent_id_claims_entities_entity_id_get) | **GET** /agents/{agent_id}/claims/entities/{entity_id} | Get an entity&#x27;s curation dossier
[**get_org_stability_summary_endpoint_org_claims_stability_get**](ClaimsApi.md#get_org_stability_summary_endpoint_org_claims_stability_get) | **GET** /org/claims/stability | Read how warm every agent&#x27;s claim corpus is across the tenant
[**get_review_context_endpoint_agents_agent_id_claims_claim_id_review_context_get**](ClaimsApi.md#get_review_context_endpoint_agents_agent_id_claims_claim_id_review_context_get) | **GET** /agents/{agent_id}/claims/{claim_id}/review-context | Get a claim&#x27;s review context and consent token
[**get_stability_summary_endpoint_agents_agent_id_claims_stability_get**](ClaimsApi.md#get_stability_summary_endpoint_agents_agent_id_claims_stability_get) | **GET** /agents/{agent_id}/claims/stability | Read how warm this agent&#x27;s claim corpus is
[**list_abstained_queue_endpoint_org_claims_abstained_get**](ClaimsApi.md#list_abstained_queue_endpoint_org_claims_abstained_get) | **GET** /org/claims/abstained | List abstained claims across the tenant
[**list_attribute_merges_endpoint_agents_agent_id_claims_attribute_merges_get**](ClaimsApi.md#list_attribute_merges_endpoint_agents_agent_id_claims_attribute_merges_get) | **GET** /agents/{agent_id}/claims/attribute-merges | List attribute merge edges
[**list_entity_aliases_endpoint_agents_agent_id_claims_entities_entity_id_aliases_get**](ClaimsApi.md#list_entity_aliases_endpoint_agents_agent_id_claims_entities_entity_id_aliases_get) | **GET** /agents/{agent_id}/claims/entities/{entity_id}/aliases | List aliases for an entity
[**list_quarantine_queue_endpoint_org_claims_quarantine_get**](ClaimsApi.md#list_quarantine_queue_endpoint_org_claims_quarantine_get) | **GET** /org/claims/quarantine | List quarantined claims across the tenant
[**list_split_proposal_queue_endpoint_org_claims_split_proposals_get**](ClaimsApi.md#list_split_proposal_queue_endpoint_org_claims_split_proposals_get) | **GET** /org/claims/split-proposals | List open split proposals across the tenant
[**promote_claim_endpoint_agents_agent_id_claims_claim_id_promote_post**](ClaimsApi.md#promote_claim_endpoint_agents_agent_id_claims_claim_id_promote_post) | **POST** /agents/{agent_id}/claims/{claim_id}/promote | Promote a disputed claim to the binding version
[**release_claim_endpoint_agents_agent_id_claims_claim_id_release_post**](ClaimsApi.md#release_claim_endpoint_agents_agent_id_claims_claim_id_release_post) | **POST** /agents/{agent_id}/claims/{claim_id}/release | Release a quarantined claim (curator path)
[**resolve_split_proposal_endpoint_agents_agent_id_claims_split_proposals_proposal_id_resolve_post**](ClaimsApi.md#resolve_split_proposal_endpoint_agents_agent_id_claims_split_proposals_proposal_id_resolve_post) | **POST** /agents/{agent_id}/claims/split-proposals/{proposal_id}/resolve | Confirm or reject a split proposal
[**reverse_attribute_merge_endpoint_agents_agent_id_claims_attribute_merges_merge_id_reverse_post**](ClaimsApi.md#reverse_attribute_merge_endpoint_agents_agent_id_claims_attribute_merges_merge_id_reverse_post) | **POST** /agents/{agent_id}/claims/attribute-merges/{merge_id}/reverse | Withdraw an attribute merge

# **admin_release_claim_endpoint_agents_agent_id_claims_claim_id_admin_release_post**
> CuratedClaim admin_release_claim_endpoint_agents_agent_id_claims_claim_id_admin_release_post(agent_id, claim_id, if_match=if_match)

Release a quarantined claim (administrator path)

Release any quarantined claim, including an untrusted (possible-injection) one, with re-verification. Admin-tier because releasing attacker-reachable content into a corpus the planner reads is the sharpest curation action. Requires the If-Match consent token.

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
claim_id = NULL # object | Claim UUID returned by a curation queue, dossier, or review-context endpoint.
if_match = NULL # object | The consent ETag returned by GET .../review-context. Required for release, promote and adopt: it proves the reviewer saw this claim's state, and a stale token is refused. (optional)

try:
    # Release a quarantined claim (administrator path)
    api_response = api_instance.admin_release_claim_endpoint_agents_agent_id_claims_claim_id_admin_release_post(agent_id, claim_id, if_match=if_match)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->admin_release_claim_endpoint_agents_agent_id_claims_claim_id_admin_release_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **claim_id** | [**object**](.md)| Claim UUID returned by a curation queue, dossier, or review-context endpoint. |
 **if_match** | [**object**](.md)| The consent ETag returned by GET .../review-context. Required for release, promote and adopt: it proves the reviewer saw this claim&#x27;s state, and a stale token is refused. | [optional]

### Return type

[**CuratedClaim**](CuratedClaim.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **adopt_claim_endpoint_agents_agent_id_claims_claim_id_adopt_post**
> CuratedClaim adopt_claim_endpoint_agents_agent_id_claims_claim_id_adopt_post(body, agent_id, claim_id, if_match=if_match)

Adopt an abstained claim under a structural attribute

Assign a structural attribute key to a claim stored without one, with the operator's attestation, so it can participate in supersession. A second adoption returns 409. Requires the If-Match consent token.

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
body = hyperstruck.AdoptClaimRequest() # AdoptClaimRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
claim_id = NULL # object | Claim UUID returned by a curation queue, dossier, or review-context endpoint.
if_match = NULL # object | The consent ETag returned by GET .../review-context. Required for release, promote and adopt: it proves the reviewer saw this claim's state, and a stale token is refused. (optional)

try:
    # Adopt an abstained claim under a structural attribute
    api_response = api_instance.adopt_claim_endpoint_agents_agent_id_claims_claim_id_adopt_post(body, agent_id, claim_id, if_match=if_match)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->adopt_claim_endpoint_agents_agent_id_claims_claim_id_adopt_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**AdoptClaimRequest**](AdoptClaimRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **claim_id** | [**object**](.md)| Claim UUID returned by a curation queue, dossier, or review-context endpoint. |
 **if_match** | [**object**](.md)| The consent ETag returned by GET .../review-context. Required for release, promote and adopt: it proves the reviewer saw this claim&#x27;s state, and a stale token is refused. | [optional]

### Return type

[**CuratedClaim**](CuratedClaim.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **create_alias_endpoint_agents_agent_id_claims_entities_entity_id_aliases_post**
> AliasResponse create_alias_endpoint_agents_agent_id_claims_entities_entity_id_aliases_post(body, agent_id, entity_id)

Author an alias for an entity

Create a reversible alias edge from an observed surface form to an entity. A sequential retry with the same text returns the existing active alias rather than duplicating it; genuinely concurrent authorings may still both insert, and either can be deactivated. Deactivating an alias does not re-split claims already folded onto the entity while it was active.

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
body = hyperstruck.CreateAliasRequest() # CreateAliasRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
entity_id = NULL # object | Claim entity UUID (the unit of identity and of erasure).

try:
    # Author an alias for an entity
    api_response = api_instance.create_alias_endpoint_agents_agent_id_claims_entities_entity_id_aliases_post(body, agent_id, entity_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->create_alias_endpoint_agents_agent_id_claims_entities_entity_id_aliases_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**CreateAliasRequest**](CreateAliasRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **entity_id** | [**object**](.md)| Claim entity UUID (the unit of identity and of erasure). |

### Return type

[**AliasResponse**](AliasResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **deactivate_alias_endpoint_agents_agent_id_claims_aliases_alias_id_deactivate_post**
> AliasResponse deactivate_alias_endpoint_agents_agent_id_claims_aliases_alias_id_deactivate_post(agent_id, alias_id)

Deactivate an alias

Toggle an alias edge off. Reversible; never a hard merge.

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
alias_id = NULL # object | Claim alias UUID returned by the alias authoring endpoint.

try:
    # Deactivate an alias
    api_response = api_instance.deactivate_alias_endpoint_agents_agent_id_claims_aliases_alias_id_deactivate_post(agent_id, alias_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->deactivate_alias_endpoint_agents_agent_id_claims_aliases_alias_id_deactivate_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **alias_id** | [**object**](.md)| Claim alias UUID returned by the alias authoring endpoint. |

### Return type

[**AliasResponse**](AliasResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **erase_entity_endpoint_agents_agent_id_claims_entities_entity_id_erasure_post**
> ClaimErasureReceipt erase_entity_endpoint_agents_agent_id_claims_entities_entity_id_erasure_post(agent_id, entity_id)

Erase an entity's claim layer

Delete an entity and its claims, aliases, dossier and split proposals, and record a durable, PII-free receipt. Before the delete, the reinforcement each of those claims earned is subtracted back out of the rules it fed, so no rule keeps standing granted by erased evidence. Idempotent: a repeat request returns the original receipt. This is still a claim-layer erasure, not a full Article 17 erasure: learnings themselves, graph nodes, raw run traces and usage aggregates are not deleted, and the receipt names each. The ledger is designed so those fan-out legs can replay against requests served today.

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

try:
    # Erase an entity's claim layer
    api_response = api_instance.erase_entity_endpoint_agents_agent_id_claims_entities_entity_id_erasure_post(agent_id, entity_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->erase_entity_endpoint_agents_agent_id_claims_entities_entity_id_erasure_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **entity_id** | [**object**](.md)| Claim entity UUID (the unit of identity and of erasure). |

### Return type

[**ClaimErasureReceipt**](ClaimErasureReceipt.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_attribute_endpoint_agents_agent_id_claims_attributes_attribute_id_get**
> AttributeRef get_attribute_endpoint_agents_agent_id_claims_attributes_attribute_id_get(agent_id, attribute_id)

Resolve a claim attribute registry id

Returns the attribute_key for a registry UUID so a curator can confirm they are adopting an abstained claim under the intended filing slot before the one-shot adopt.

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
attribute_id = NULL # object | Claim attribute registry UUID (filing slot for structured facts).

try:
    # Resolve a claim attribute registry id
    api_response = api_instance.get_attribute_endpoint_agents_agent_id_claims_attributes_attribute_id_get(agent_id, attribute_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->get_attribute_endpoint_agents_agent_id_claims_attributes_attribute_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **attribute_id** | [**object**](.md)| Claim attribute registry UUID (filing slot for structured facts). |

### Return type

[**AttributeRef**](AttributeRef.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_entity_dossier_endpoint_agents_agent_id_claims_entities_entity_id_get**
> ClaimDossierResponse get_entity_dossier_endpoint_agents_agent_id_claims_entities_entity_id_get(agent_id, entity_id)

Get an entity's curation dossier

Every version of every claim the agent holds about one entity, including quarantined and disputed versions the agent-facing recall path never surfaces. Answers what the agent knows about this entity, on whose word, and since when.

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

try:
    # Get an entity's curation dossier
    api_response = api_instance.get_entity_dossier_endpoint_agents_agent_id_claims_entities_entity_id_get(agent_id, entity_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->get_entity_dossier_endpoint_agents_agent_id_claims_entities_entity_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **entity_id** | [**object**](.md)| Claim entity UUID (the unit of identity and of erasure). |

### Return type

[**ClaimDossierResponse**](ClaimDossierResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_org_stability_summary_endpoint_org_claims_stability_get**
> OrgClaimStabilitySummary get_org_stability_summary_endpoint_org_claims_stability_get(limit=limit)

Read how warm every agent's claim corpus is across the tenant

The per-agent stability readings the decision to enable the plan-rewrite pass is taken on, plus the tenant total. The decision is per agent but reviewed per tenant, and this is the view that makes that possible without knowing every agent id. is_truncated says the tenant has more agents than limit, so the total covers only the agents listed. See the claim curation API guide for how to interpret each population.

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
limit = 50 # object | Maximum number of items to return on this page. (optional) (default to 50)

try:
    # Read how warm every agent's claim corpus is across the tenant
    api_response = api_instance.get_org_stability_summary_endpoint_org_claims_stability_get(limit=limit)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->get_org_stability_summary_endpoint_org_claims_stability_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 50]

### Return type

[**OrgClaimStabilitySummary**](OrgClaimStabilitySummary.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_review_context_endpoint_agents_agent_id_claims_claim_id_review_context_get**
> ClaimReviewContext get_review_context_endpoint_agents_agent_id_claims_claim_id_review_context_get(agent_id, claim_id)

Get a claim's review context and consent token

The provenance, quarantine reason and corroboration a reviewer must see before releasing a claim, plus an ETag consent token. Pass the ETag back as If-Match on release, promote or adopt; any change to the claim invalidates it.

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
claim_id = NULL # object | Claim UUID returned by a curation queue, dossier, or review-context endpoint.

try:
    # Get a claim's review context and consent token
    api_response = api_instance.get_review_context_endpoint_agents_agent_id_claims_claim_id_review_context_get(agent_id, claim_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->get_review_context_endpoint_agents_agent_id_claims_claim_id_review_context_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **claim_id** | [**object**](.md)| Claim UUID returned by a curation queue, dossier, or review-context endpoint. |

### Return type

[**ClaimReviewContext**](ClaimReviewContext.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_stability_summary_endpoint_agents_agent_id_claims_stability_get**
> ClaimStabilitySummary get_stability_summary_endpoint_agents_agent_id_claims_stability_get(agent_id)

Read how warm this agent's claim corpus is

The slot populations the decision to enable the plan-rewrite pass is taken on, and the confidence and prior_changes they were evaluated at. Read admitted_slots as a series, not a single number, and as an upper bound on read elimination rather than a count of it. See the claim curation API guide for how to interpret each population.

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

try:
    # Read how warm this agent's claim corpus is
    api_response = api_instance.get_stability_summary_endpoint_agents_agent_id_claims_stability_get(agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->get_stability_summary_endpoint_agents_agent_id_claims_stability_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

[**ClaimStabilitySummary**](ClaimStabilitySummary.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_abstained_queue_endpoint_org_claims_abstained_get**
> AbstainedQueueResponse list_abstained_queue_endpoint_org_claims_abstained_get(limit=limit, cursor=cursor)

List abstained claims across the tenant

Claims stored without a structural attribute key, awaiting adoption under one. Fanned across the tenant's agents and labelled with the owning agent. recorded_at keyset pagination.

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
limit = 50 # object | Maximum number of items to return on this page. (optional) (default to 50)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)

try:
    # List abstained claims across the tenant
    api_response = api_instance.list_abstained_queue_endpoint_org_claims_abstained_get(limit=limit, cursor=cursor)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->list_abstained_queue_endpoint_org_claims_abstained_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 50]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]

### Return type

[**AbstainedQueueResponse**](AbstainedQueueResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_attribute_merges_endpoint_agents_agent_id_claims_attribute_merges_get**
> AttributeMergesResponse list_attribute_merges_endpoint_agents_agent_id_claims_attribute_merges_get(agent_id)

List attribute merge edges

Every assertion that two attribute keys name the same property, newest first, active and withdrawn alike. A withdrawn edge is kept rather than deleted, because the supersessions it caused are recorded against it.

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

try:
    # List attribute merge edges
    api_response = api_instance.list_attribute_merges_endpoint_agents_agent_id_claims_attribute_merges_get(agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->list_attribute_merges_endpoint_agents_agent_id_claims_attribute_merges_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

[**AttributeMergesResponse**](AttributeMergesResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_entity_aliases_endpoint_agents_agent_id_claims_entities_entity_id_aliases_get**
> EntityAliasesResponse list_entity_aliases_endpoint_agents_agent_id_claims_entities_entity_id_aliases_get(agent_id, entity_id)

List aliases for an entity

Every alias surface form linked to this entity (active and inactive), newest first. Used by the curation console so a reviewer can see which names already fold onto the entity before authoring another.

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

try:
    # List aliases for an entity
    api_response = api_instance.list_entity_aliases_endpoint_agents_agent_id_claims_entities_entity_id_aliases_get(agent_id, entity_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->list_entity_aliases_endpoint_agents_agent_id_claims_entities_entity_id_aliases_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **entity_id** | [**object**](.md)| Claim entity UUID (the unit of identity and of erasure). |

### Return type

[**EntityAliasesResponse**](EntityAliasesResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_quarantine_queue_endpoint_org_claims_quarantine_get**
> QuarantineQueueResponse list_quarantine_queue_endpoint_org_claims_quarantine_get(limit=limit, cursor=cursor)

List quarantined claims across the tenant

The tenant's quarantined claims, fanned across its agents and each labelled with its owning agent. A quarantined claim is a possible injection or a high-stakes supersession that a human must judge before it can bind. recorded_at keyset pagination.

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
limit = 50 # object | Maximum number of items to return on this page. (optional) (default to 50)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)

try:
    # List quarantined claims across the tenant
    api_response = api_instance.list_quarantine_queue_endpoint_org_claims_quarantine_get(limit=limit, cursor=cursor)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->list_quarantine_queue_endpoint_org_claims_quarantine_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 50]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]

### Return type

[**QuarantineQueueResponse**](QuarantineQueueResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_split_proposal_queue_endpoint_org_claims_split_proposals_get**
> SplitProposalQueueResponse list_split_proposal_queue_endpoint_org_claims_split_proposals_get(limit=limit, cursor=cursor)

List open split proposals across the tenant

Proposals that an oscillating attribute key be split into qualified variants rather than repeatedly superseded. Fanned across the tenant's agents and labelled with the owning agent. created_at keyset pagination.

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
limit = 50 # object | Maximum number of items to return on this page. (optional) (default to 50)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)

try:
    # List open split proposals across the tenant
    api_response = api_instance.list_split_proposal_queue_endpoint_org_claims_split_proposals_get(limit=limit, cursor=cursor)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->list_split_proposal_queue_endpoint_org_claims_split_proposals_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 50]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]

### Return type

[**SplitProposalQueueResponse**](SplitProposalQueueResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **promote_claim_endpoint_agents_agent_id_claims_claim_id_promote_post**
> CuratedClaim promote_claim_endpoint_agents_agent_id_claims_claim_id_promote_post(body, agent_id, claim_id, if_match=if_match)

Promote a disputed claim to the binding version

Make a disputed alternative the open, binding version for its key, with the operator's attestation. A second promotion of the same claim returns 409. Requires the If-Match consent token.

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
body = hyperstruck.PromoteClaimRequest() # PromoteClaimRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
claim_id = NULL # object | Claim UUID returned by a curation queue, dossier, or review-context endpoint.
if_match = NULL # object | The consent ETag returned by GET .../review-context. Required for release, promote and adopt: it proves the reviewer saw this claim's state, and a stale token is refused. (optional)

try:
    # Promote a disputed claim to the binding version
    api_response = api_instance.promote_claim_endpoint_agents_agent_id_claims_claim_id_promote_post(body, agent_id, claim_id, if_match=if_match)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->promote_claim_endpoint_agents_agent_id_claims_claim_id_promote_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**PromoteClaimRequest**](PromoteClaimRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **claim_id** | [**object**](.md)| Claim UUID returned by a curation queue, dossier, or review-context endpoint. |
 **if_match** | [**object**](.md)| The consent ETag returned by GET .../review-context. Required for release, promote and adopt: it proves the reviewer saw this claim&#x27;s state, and a stale token is refused. | [optional]

### Return type

[**CuratedClaim**](CuratedClaim.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **release_claim_endpoint_agents_agent_id_claims_claim_id_release_post**
> CuratedClaim release_claim_endpoint_agents_agent_id_claims_claim_id_release_post(agent_id, claim_id, if_match=if_match)

Release a quarantined claim (curator path)

Release a curator-releasable quarantined claim (high-stakes or a lapsed endorsement), re-entering it into verification with the operator's attestation. Any other reason, an untrusted (possible-injection) claim, an unresolved-identity or unclassified one, or a claim with no recorded reason, is refused here and must go through the admin release. Requires the If-Match consent token.

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
claim_id = NULL # object | Claim UUID returned by a curation queue, dossier, or review-context endpoint.
if_match = NULL # object | The consent ETag returned by GET .../review-context. Required for release, promote and adopt: it proves the reviewer saw this claim's state, and a stale token is refused. (optional)

try:
    # Release a quarantined claim (curator path)
    api_response = api_instance.release_claim_endpoint_agents_agent_id_claims_claim_id_release_post(agent_id, claim_id, if_match=if_match)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->release_claim_endpoint_agents_agent_id_claims_claim_id_release_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **claim_id** | [**object**](.md)| Claim UUID returned by a curation queue, dossier, or review-context endpoint. |
 **if_match** | [**object**](.md)| The consent ETag returned by GET .../review-context. Required for release, promote and adopt: it proves the reviewer saw this claim&#x27;s state, and a stale token is refused. | [optional]

### Return type

[**CuratedClaim**](CuratedClaim.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **resolve_split_proposal_endpoint_agents_agent_id_claims_split_proposals_proposal_id_resolve_post**
> ResolveSplitResponse resolve_split_proposal_endpoint_agents_agent_id_claims_split_proposals_proposal_id_resolve_post(body, agent_id, proposal_id)

Confirm or reject a split proposal

Resolve an oscillating-key split proposal. Refuses to re-resolve one that is already confirmed or rejected (409).

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
body = hyperstruck.ResolveSplitRequest() # ResolveSplitRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
proposal_id = NULL # object | Split-proposal UUID returned by the split-proposal queue.

try:
    # Confirm or reject a split proposal
    api_response = api_instance.resolve_split_proposal_endpoint_agents_agent_id_claims_split_proposals_proposal_id_resolve_post(body, agent_id, proposal_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->resolve_split_proposal_endpoint_agents_agent_id_claims_split_proposals_proposal_id_resolve_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ResolveSplitRequest**](ResolveSplitRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **proposal_id** | [**object**](.md)| Split-proposal UUID returned by the split-proposal queue. |

### Return type

[**ResolveSplitResponse**](ResolveSplitResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **reverse_attribute_merge_endpoint_agents_agent_id_claims_attribute_merges_merge_id_reverse_post**
> AttributeMergeReversalResponse reverse_attribute_merge_endpoint_agents_agent_id_claims_attribute_merges_merge_id_reverse_post(agent_id, merge_id)

Withdraw an attribute merge

Withdraw a merge and reopen exactly the versions it closed. The repair path for the one destructive operation in the claim layer: a wrong merge folds two unrelated properties into one history and the earlier one silently stops binding. Repairs beliefs, not actions.

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
merge_id = NULL # object | Attribute merge edge UUID returned by the merge listing endpoint.

try:
    # Withdraw an attribute merge
    api_response = api_instance.reverse_attribute_merge_endpoint_agents_agent_id_claims_attribute_merges_merge_id_reverse_post(agent_id, merge_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->reverse_attribute_merge_endpoint_agents_agent_id_claims_attribute_merges_merge_id_reverse_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **merge_id** | [**object**](.md)| Attribute merge edge UUID returned by the merge listing endpoint. |

### Return type

[**AttributeMergeReversalResponse**](AttributeMergeReversalResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

