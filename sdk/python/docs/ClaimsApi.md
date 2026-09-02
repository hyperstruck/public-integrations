# hyperstruck.ClaimsApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**admin_release_claim_endpoint_agents_agent_id_claims_claim_id_admin_release_post**](ClaimsApi.md#admin_release_claim_endpoint_agents_agent_id_claims_claim_id_admin_release_post) | **POST** /agents/{agent_id}/claims/{claim_id}/admin-release | Release a quarantined claim (administrator path)
[**adopt_claim_endpoint_agents_agent_id_claims_claim_id_adopt_post**](ClaimsApi.md#adopt_claim_endpoint_agents_agent_id_claims_claim_id_adopt_post) | **POST** /agents/{agent_id}/claims/{claim_id}/adopt | Adopt an abstained claim under a structural attribute
[**answer_endpoint_agents_agent_id_answer_post**](ClaimsApi.md#answer_endpoint_agents_agent_id_answer_post) | **POST** /agents/{agent_id}/answer | Answer a question from the documents that concern it
[**apply_harness_repair_endpoint_agents_agent_id_claims_harness_repair_apply_post**](ClaimsApi.md#apply_harness_repair_endpoint_agents_agent_id_claims_harness_repair_apply_post) | **POST** /agents/{agent_id}/claims/harness-repair/apply | Erase the approved harness-shaped entities
[**create_alias_endpoint_agents_agent_id_claims_entities_entity_id_aliases_post**](ClaimsApi.md#create_alias_endpoint_agents_agent_id_claims_entities_entity_id_aliases_post) | **POST** /agents/{agent_id}/claims/entities/{entity_id}/aliases | Author an alias for an entity
[**deactivate_alias_endpoint_agents_agent_id_claims_aliases_alias_id_deactivate_post**](ClaimsApi.md#deactivate_alias_endpoint_agents_agent_id_claims_aliases_alias_id_deactivate_post) | **POST** /agents/{agent_id}/claims/aliases/{alias_id}/deactivate | Deactivate an alias
[**erase_entity_endpoint_agents_agent_id_claims_entities_entity_id_erasure_post**](ClaimsApi.md#erase_entity_endpoint_agents_agent_id_claims_entities_entity_id_erasure_post) | **POST** /agents/{agent_id}/claims/entities/{entity_id}/erasure | Erase an entity&#x27;s claim layer
[**get_attribute_endpoint_agents_agent_id_claims_attributes_attribute_id_get**](ClaimsApi.md#get_attribute_endpoint_agents_agent_id_claims_attributes_attribute_id_get) | **GET** /agents/{agent_id}/claims/attributes/{attribute_id} | Resolve a claim attribute registry id
[**get_entity_dossier_endpoint_agents_agent_id_claims_entities_entity_id_get**](ClaimsApi.md#get_entity_dossier_endpoint_agents_agent_id_claims_entities_entity_id_get) | **GET** /agents/{agent_id}/claims/entities/{entity_id} | Get an entity&#x27;s curation dossier
[**get_erasure_receipt_endpoint_agents_agent_id_claims_entities_entity_id_erasure_get**](ClaimsApi.md#get_erasure_receipt_endpoint_agents_agent_id_claims_entities_entity_id_erasure_get) | **GET** /agents/{agent_id}/claims/entities/{entity_id}/erasure | Read one entity&#x27;s erasure receipt
[**get_org_claims_summary_endpoint_org_claims_summary_get**](ClaimsApi.md#get_org_claims_summary_endpoint_org_claims_summary_get) | **GET** /org/claims/summary | Count each agent&#x27;s claims waiting in the tenant queues
[**get_org_stability_summary_endpoint_org_claims_stability_get**](ClaimsApi.md#get_org_stability_summary_endpoint_org_claims_stability_get) | **GET** /org/claims/stability | Read how warm every agent&#x27;s claim corpus is across the tenant
[**get_review_context_endpoint_agents_agent_id_claims_claim_id_review_context_get**](ClaimsApi.md#get_review_context_endpoint_agents_agent_id_claims_claim_id_review_context_get) | **GET** /agents/{agent_id}/claims/{claim_id}/review-context | Get a claim&#x27;s review context and consent token
[**get_shadowed_bind_surfaces_endpoint_agents_agent_id_claims_shadowed_surfaces_get**](ClaimsApi.md#get_shadowed_bind_surfaces_endpoint_agents_agent_id_claims_shadowed_surfaces_get) | **GET** /agents/{agent_id}/claims/shadowed-surfaces | Find registered names an agent&#x27;s own goals cannot reach
[**get_split_proposal_endpoint_agents_agent_id_claims_split_proposals_proposal_id_get**](ClaimsApi.md#get_split_proposal_endpoint_agents_agent_id_claims_split_proposals_proposal_id_get) | **GET** /agents/{agent_id}/claims/split-proposals/{proposal_id} | Read one split proposal
[**get_stability_summary_endpoint_agents_agent_id_claims_stability_get**](ClaimsApi.md#get_stability_summary_endpoint_agents_agent_id_claims_stability_get) | **GET** /agents/{agent_id}/claims/stability | Read how warm this agent&#x27;s claim corpus is
[**list_abstained_queue_endpoint_org_claims_abstained_get**](ClaimsApi.md#list_abstained_queue_endpoint_org_claims_abstained_get) | **GET** /org/claims/abstained | List abstained claims across the tenant
[**list_agent_claims_endpoint_agents_agent_id_claims_get**](ClaimsApi.md#list_agent_claims_endpoint_agents_agent_id_claims_get) | **GET** /agents/{agent_id}/claims | List an agent&#x27;s claims
[**list_answers_endpoint_agents_agent_id_answers_get**](ClaimsApi.md#list_answers_endpoint_agents_agent_id_answers_get) | **GET** /agents/{agent_id}/answers | The answers this agent gave in the last 30 days
[**list_attribute_merges_endpoint_agents_agent_id_claims_attribute_merges_get**](ClaimsApi.md#list_attribute_merges_endpoint_agents_agent_id_claims_attribute_merges_get) | **GET** /agents/{agent_id}/claims/attribute-merges | List attribute merge edges
[**list_attributes_endpoint_agents_agent_id_claims_attributes_get**](ClaimsApi.md#list_attributes_endpoint_agents_agent_id_claims_attributes_get) | **GET** /agents/{agent_id}/claims/attributes | List this agent&#x27;s attribute registry
[**list_entity_aliases_endpoint_agents_agent_id_claims_entities_entity_id_aliases_get**](ClaimsApi.md#list_entity_aliases_endpoint_agents_agent_id_claims_entities_entity_id_aliases_get) | **GET** /agents/{agent_id}/claims/entities/{entity_id}/aliases | List aliases for an entity
[**list_entity_merges_endpoint_agents_agent_id_claims_entity_merges_get**](ClaimsApi.md#list_entity_merges_endpoint_agents_agent_id_claims_entity_merges_get) | **GET** /agents/{agent_id}/claims/entity-merges | List entity merge edges
[**list_erasures_endpoint_agents_agent_id_claims_erasures_get**](ClaimsApi.md#list_erasures_endpoint_agents_agent_id_claims_erasures_get) | **GET** /agents/{agent_id}/claims/erasures | List this agent&#x27;s erasure receipts
[**list_quarantine_queue_endpoint_org_claims_quarantine_get**](ClaimsApi.md#list_quarantine_queue_endpoint_org_claims_quarantine_get) | **GET** /org/claims/quarantine | List quarantined claims across the tenant
[**list_split_proposal_queue_endpoint_org_claims_split_proposals_get**](ClaimsApi.md#list_split_proposal_queue_endpoint_org_claims_split_proposals_get) | **GET** /org/claims/split-proposals | List open split proposals across the tenant
[**plan_harness_repair_endpoint_agents_agent_id_claims_harness_repair_plan_get**](ClaimsApi.md#plan_harness_repair_endpoint_agents_agent_id_claims_harness_repair_plan_get) | **GET** /agents/{agent_id}/claims/harness-repair/plan | Plan the repair of claims minted from harness text
[**promote_claim_endpoint_agents_agent_id_claims_claim_id_promote_post**](ClaimsApi.md#promote_claim_endpoint_agents_agent_id_claims_claim_id_promote_post) | **POST** /agents/{agent_id}/claims/{claim_id}/promote | Promote a disputed claim to the binding version
[**propose_split_endpoint_agents_agent_id_claims_claim_id_propose_split_post**](ClaimsApi.md#propose_split_endpoint_agents_agent_id_claims_claim_id_propose_split_post) | **POST** /agents/{agent_id}/claims/{claim_id}/propose-split | Propose a split so two true values can coexist
[**read_claims_for_question_endpoint_agents_agent_id_claims_question_post**](ClaimsApi.md#read_claims_for_question_endpoint_agents_agent_id_claims_question_post) | **POST** /agents/{agent_id}/claims/question | Answer a question from an agent&#x27;s claims
[**release_claim_endpoint_agents_agent_id_claims_claim_id_release_post**](ClaimsApi.md#release_claim_endpoint_agents_agent_id_claims_claim_id_release_post) | **POST** /agents/{agent_id}/claims/{claim_id}/release | Release a quarantined claim (curator path)
[**resolve_split_proposal_endpoint_agents_agent_id_claims_split_proposals_proposal_id_resolve_post**](ClaimsApi.md#resolve_split_proposal_endpoint_agents_agent_id_claims_split_proposals_proposal_id_resolve_post) | **POST** /agents/{agent_id}/claims/split-proposals/{proposal_id}/resolve | Confirm or reject a split proposal
[**reverse_attribute_merge_endpoint_agents_agent_id_claims_attribute_merges_merge_id_reverse_post**](ClaimsApi.md#reverse_attribute_merge_endpoint_agents_agent_id_claims_attribute_merges_merge_id_reverse_post) | **POST** /agents/{agent_id}/claims/attribute-merges/{merge_id}/reverse | Withdraw an attribute merge
[**reverse_entity_merge_endpoint_agents_agent_id_claims_entity_merges_merge_id_reverse_post**](ClaimsApi.md#reverse_entity_merge_endpoint_agents_agent_id_claims_entity_merges_merge_id_reverse_post) | **POST** /agents/{agent_id}/claims/entity-merges/{merge_id}/reverse | Withdraw an entity merge
[**stored_answer_endpoint_agents_agent_id_answers_answer_id_get**](ClaimsApi.md#stored_answer_endpoint_agents_agent_id_answers_answer_id_get) | **GET** /agents/{agent_id}/answers/{answer_id} | The same answer, at another level of detail
[**wipe_agent_claims_endpoint_agents_agent_id_claims_delete**](ClaimsApi.md#wipe_agent_claims_endpoint_agents_agent_id_claims_delete) | **DELETE** /agents/{agent_id}/claims | Erase a batch of this agent&#x27;s entities and their claim layer

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
if_match = NULL # object | The consent ETag returned by GET .../review-context. Required for release, promote, adopt and propose-split: it proves the reviewer saw this claim's state, and a stale token is refused. (optional)

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
 **if_match** | [**object**](.md)| The consent ETag returned by GET .../review-context. Required for release, promote, adopt and propose-split: it proves the reviewer saw this claim&#x27;s state, and a stale token is refused. | [optional]

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
if_match = NULL # object | The consent ETag returned by GET .../review-context. Required for release, promote, adopt and propose-split: it proves the reviewer saw this claim's state, and a stale token is refused. (optional)

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
 **if_match** | [**object**](.md)| The consent ETag returned by GET .../review-context. Required for release, promote, adopt and propose-split: it proves the reviewer saw this claim&#x27;s state, and a stale token is refused. | [optional]

### Return type

[**CuratedClaim**](CuratedClaim.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **answer_endpoint_agents_agent_id_answer_post**
> AnswerView answer_endpoint_agents_agent_id_answer_post(body, agent_id, idempotency_key=idempotency_key)

Answer a question from the documents that concern it

Reads the documents linked to the accounts your question names, and the documents its wording reaches, latest first, then writes an answer from what each one says.  Read `answer`; it can be null with a typed reason.  The default `detail=answer` level returns the answer, its `references`, the documents they name, `completeness` and `silence`; `completeness` is returned at every level. `detail=findings` adds `lead`, `findings`, `sections`, `results`, `appended_finding_ids`, `background_finding_ids`, `interpretation`, `subject`, `selection`, `multi_valued_slots`, `boundary`, `change`, `obligations`; `detail=claims` adds `claims`; `detail=everything` adds `read_documents`, `sources`, `stage_events`. Each level is the one before it plus its additions. A section at or below the level asked for is null when the step that produces it did not run for this answer, and an empty list when it ran and found nothing.  `budget_chars` lowers or raises how much document text is read, up to a ceiling. Past the budget the latest meetings are read first and the rest are chosen for relevance, labelled `earlier_history` so they are never stated as the current position.  Obligations are read at the time of the call rather than at `as_of`, which `obligations.is_as_of_pinned` states. Needs `claims:read` AND `agents:read`.  Synchronous, bounded only against a hang. The whole answer is stored as given for 30 days regardless of the `detail` asked for, so `GET /agents/{agent_id}/answers/{answer_id}` serves it again, word for word, at any level up to the one it names in `more`. A reused Idempotency-Key returns that same stored answer rather than composing again; a withheld answer is never billed and never holds the key, so a retry with it composes fresh. It earns no attribution.

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
body = hyperstruck.AnswerRequest() # AnswerRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
idempotency_key = NULL # object | Makes a retry safe: a repeat of a key this agent used in the last 30 days returns the answer already given, at the requested level, and bills nothing. A withheld answer never holds the key, so a retry with it composes fresh instead. (optional)

try:
    # Answer a question from the documents that concern it
    api_response = api_instance.answer_endpoint_agents_agent_id_answer_post(body, agent_id, idempotency_key=idempotency_key)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->answer_endpoint_agents_agent_id_answer_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**AnswerRequest**](AnswerRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **idempotency_key** | [**object**](.md)| Makes a retry safe: a repeat of a key this agent used in the last 30 days returns the answer already given, at the requested level, and bills nothing. A withheld answer never holds the key, so a retry with it composes fresh instead. | [optional]

### Return type

[**AnswerView**](AnswerView.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apply_harness_repair_endpoint_agents_agent_id_claims_harness_repair_apply_post**
> HarnessRepairOutcome apply_harness_repair_endpoint_agents_agent_id_claims_harness_repair_apply_post(body, agent_id, if_match=if_match)

Erase the approved harness-shaped entities

Erase the entities named in the body, through the same cascade and the same durable receipt the single-entity erasure writes, so no rule is left standing on evidence that is gone. The plan is re-derived first and only the intersection is erased: an entity that gained a real claim since the plan was read is reported as skipped rather than erased on stale evidence. Bounded per request; the remainder is reported and needs no resume, because an erased entity leaves the registry and the next plan is simply smaller. Requires the If-Match consent token from the plan.

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
body = hyperstruck.ApplyHarnessRepairRequest() # ApplyHarnessRepairRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
if_match = NULL # object | The consent ETag returned by GET .../review-context. Required for release, promote, adopt and propose-split: it proves the reviewer saw this claim's state, and a stale token is refused. (optional)

try:
    # Erase the approved harness-shaped entities
    api_response = api_instance.apply_harness_repair_endpoint_agents_agent_id_claims_harness_repair_apply_post(body, agent_id, if_match=if_match)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->apply_harness_repair_endpoint_agents_agent_id_claims_harness_repair_apply_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ApplyHarnessRepairRequest**](ApplyHarnessRepairRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **if_match** | [**object**](.md)| The consent ETag returned by GET .../review-context. Required for release, promote, adopt and propose-split: it proves the reviewer saw this claim&#x27;s state, and a stale token is refused. | [optional]

### Return type

[**HarnessRepairOutcome**](HarnessRepairOutcome.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **create_alias_endpoint_agents_agent_id_claims_entities_entity_id_aliases_post**
> AliasResponse create_alias_endpoint_agents_agent_id_claims_entities_entity_id_aliases_post(body, agent_id, entity_id)

Author an alias for an entity

Assert that a surface form denotes this entity. Reversible, and never a hard merge. A retry with the same text updates the form already recorded rather than duplicating it, and re-authoring a form that was withdrawn puts it back. Deactivating a form does not re-split claims already folded onto the entity while it was active. Refused with **409** when the text is the canonical name of another entity, because recall returns a single entity per folded form and ranks a name above every other form, so the new binding could never fire. The message names the entity in the way; the remedy is to merge the two entities or rename one of them.

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

Withdraw an authored form so it stops binding. Reversible: authoring the same text again puts it back. The id is the one this entity's listing returned, whenever it was minted.

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
> ClaimErasureReceipt erase_entity_endpoint_agents_agent_id_claims_entities_entity_id_erasure_post(agent_id, entity_id, body=body)

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
body = NULL # object |  (optional)

try:
    # Erase an entity's claim layer
    api_response = api_instance.erase_entity_endpoint_agents_agent_id_claims_entities_entity_id_erasure_post(agent_id, entity_id, body=body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->erase_entity_endpoint_agents_agent_id_claims_entities_entity_id_erasure_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **entity_id** | [**object**](.md)| Claim entity UUID (the unit of identity and of erasure). |
 **body** | [**object**](object.md)|  | [optional]

### Return type

[**ClaimErasureReceipt**](ClaimErasureReceipt.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
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

# **get_erasure_receipt_endpoint_agents_agent_id_claims_entities_entity_id_erasure_get**
> ClaimErasureReceipt get_erasure_receipt_endpoint_agents_agent_id_claims_entities_entity_id_erasure_get(agent_id, entity_id)

Read one entity's erasure receipt

The receipt for an entity already erased, or 404 if it never was. The erasure POST is idempotent and returns the original receipt, so this was previously readable only by asking to erase again; an audit record should not need a destructive verb to read.

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
    # Read one entity's erasure receipt
    api_response = api_instance.get_erasure_receipt_endpoint_agents_agent_id_claims_entities_entity_id_erasure_get(agent_id, entity_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->get_erasure_receipt_endpoint_agents_agent_id_claims_entities_entity_id_erasure_get: %s\n" % e)
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

# **get_org_claims_summary_endpoint_org_claims_summary_get**
> OrgClaimsSummary get_org_claims_summary_endpoint_org_claims_summary_get()

Count each agent's claims waiting in the tenant queues

For every agent the caller can see: how many claims are held, how many need an attribute, and how many split proposals are open, counted under the caller's readable spaces with the same rules the three queues list by. Agents with nothing queued are included at zero. A deleted agent that still has queued rows is listed with is_deleted true and no name. One row per agent, so it is not paged.

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

try:
    # Count each agent's claims waiting in the tenant queues
    api_response = api_instance.get_org_claims_summary_endpoint_org_claims_summary_get()
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->get_org_claims_summary_endpoint_org_claims_summary_get: %s\n" % e)
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**OrgClaimsSummary**](OrgClaimsSummary.md)

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

# **get_shadowed_bind_surfaces_endpoint_agents_agent_id_claims_shadowed_surfaces_get**
> ShadowedBindSurfacesResponse get_shadowed_bind_surfaces_endpoint_agents_agent_id_claims_shadowed_surfaces_get(agent_id, limit=limit)

Find registered names an agent's own goals cannot reach

Recall matches a goal against a folded form of each registered name and returns one entity per folded form, so two names that fold together leave one of them unreachable by its own exact text, silently. This lists every folded form the agent registers more than once, which one a goal reaches, and whether a rule chose it. Read `is_settled_by_rank` first: true means a canonical name beat an alias, which is deliberate, and false means nothing but which row was written first decided it. Nothing here changes what binds.

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
limit = 100 # object |  (optional) (default to 100)

try:
    # Find registered names an agent's own goals cannot reach
    api_response = api_instance.get_shadowed_bind_surfaces_endpoint_agents_agent_id_claims_shadowed_surfaces_get(agent_id, limit=limit)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->get_shadowed_bind_surfaces_endpoint_agents_agent_id_claims_shadowed_surfaces_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **limit** | [**object**](.md)|  | [optional] [default to 100]

### Return type

[**ShadowedBindSurfacesResponse**](ShadowedBindSurfacesResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_split_proposal_endpoint_agents_agent_id_claims_split_proposals_proposal_id_get**
> SplitProposalQueueItem get_split_proposal_endpoint_agents_agent_id_claims_split_proposals_proposal_id_get(agent_id, proposal_id)

Read one split proposal

One of the agent's split proposals in its current state, including once it has been confirmed or rejected, so a saved link to it still opens. Another agent's proposal, or one that does not exist, is a 404.

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
proposal_id = NULL # object | Split-proposal UUID returned by the split-proposal queue.

try:
    # Read one split proposal
    api_response = api_instance.get_split_proposal_endpoint_agents_agent_id_claims_split_proposals_proposal_id_get(agent_id, proposal_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->get_split_proposal_endpoint_agents_agent_id_claims_split_proposals_proposal_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **proposal_id** | [**object**](.md)| Split-proposal UUID returned by the split-proposal queue. |

### Return type

[**SplitProposalQueueItem**](SplitProposalQueueItem.md)

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
> AbstainedQueueResponse list_abstained_queue_endpoint_org_claims_abstained_get(limit=limit, cursor=cursor, agent_id=agent_id)

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
agent_id = NULL # object | List only this agent's rows. An agent the caller cannot see, or one with nothing queued, returns the same empty page. A cursor is valid only with the filter it was issued under. (optional)

try:
    # List abstained claims across the tenant
    api_response = api_instance.list_abstained_queue_endpoint_org_claims_abstained_get(limit=limit, cursor=cursor, agent_id=agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->list_abstained_queue_endpoint_org_claims_abstained_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 50]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]
 **agent_id** | [**object**](.md)| List only this agent&#x27;s rows. An agent the caller cannot see, or one with nothing queued, returns the same empty page. A cursor is valid only with the filter it was issued under. | [optional]

### Return type

[**AbstainedQueueResponse**](AbstainedQueueResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_agent_claims_endpoint_agents_agent_id_claims_get**
> AgentClaimsListResponse list_agent_claims_endpoint_agents_agent_id_claims_get(agent_id, status=status, q=q, limit=limit, cursor=cursor)

List an agent's claims

Every claim on this agent's entity shelf, including quarantined and disputed rows the recall path will not inject. Filter by review status or search entity name and statement. recorded_at keyset pagination. Facets are corpus-wide after search, before the status filter.

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
status = all # object | Review status filter. `all` is every claim. `open` is bindable candidates: open, unquarantined, and not expired. (optional) (default to all)
q = NULL # object |  (optional)
limit = 25 # object | Maximum number of items to return on this page. (optional) (default to 25)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)

try:
    # List an agent's claims
    api_response = api_instance.list_agent_claims_endpoint_agents_agent_id_claims_get(agent_id, status=status, q=q, limit=limit, cursor=cursor)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->list_agent_claims_endpoint_agents_agent_id_claims_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **status** | [**object**](.md)| Review status filter. &#x60;all&#x60; is every claim. &#x60;open&#x60; is bindable candidates: open, unquarantined, and not expired. | [optional] [default to all]
 **q** | [**object**](.md)|  | [optional]
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 25]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]

### Return type

[**AgentClaimsListResponse**](AgentClaimsListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_answers_endpoint_agents_agent_id_answers_get**
> StoredAnswerPage list_answers_endpoint_agents_agent_id_answers_get(agent_id, cursor=cursor, limit=limit, flagged=flagged, unconfirmed=unconfirmed, withheld=withheld, q=q)

The answers this agent gave in the last 30 days

Lists the answers `POST /agents/{agent_id}/answer` gave in the last 30 days, newest first, each with its question, when it was asked and when it expires, why it was withheld if it was, and how its findings were judged. Follow an answer's `url` to read it.  Filters combine: `flagged` keeps answers with a finding the checker found not carried by its source (partly supported or unsupported), `unconfirmed` keeps answers with a finding resting on a held claim, `withheld` keeps answers that were withheld, and `q` matches the question, ignoring case. Pass `next_cursor` as `cursor` for the next page.  No model runs and nothing is billed. Needs `claims:read` AND `agents:read`, the same as the answer itself.

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
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)
limit = 25 # object | Maximum number of items to return on this page. (optional) (default to 25)
flagged = false # object |  (optional) (default to false)
unconfirmed = false # object |  (optional) (default to false)
withheld = false # object |  (optional) (default to false)
q = NULL # object |  (optional)

try:
    # The answers this agent gave in the last 30 days
    api_response = api_instance.list_answers_endpoint_agents_agent_id_answers_get(agent_id, cursor=cursor, limit=limit, flagged=flagged, unconfirmed=unconfirmed, withheld=withheld, q=q)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->list_answers_endpoint_agents_agent_id_answers_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 25]
 **flagged** | [**object**](.md)|  | [optional] [default to false]
 **unconfirmed** | [**object**](.md)|  | [optional] [default to false]
 **withheld** | [**object**](.md)|  | [optional] [default to false]
 **q** | [**object**](.md)|  | [optional]

### Return type

[**StoredAnswerPage**](StoredAnswerPage.md)

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

# **list_attributes_endpoint_agents_agent_id_claims_attributes_get**
> AttributeListResponse list_attributes_endpoint_agents_agent_id_claims_attributes_get(agent_id, q=q, limit=limit)

List this agent's attribute registry

The structural attributes an abstained claim can be filed under, for the adopt picker. Keys that lost a merge are excluded: adopt is one-shot and filing under the loser puts the claim on a version chain that no longer receives values. Unlike the claim inventory there is no minimum query length, because a registry is small enough to show whole and a curator usually cannot name the slot until they see it. A registry larger than the limit sets has_more, so the picker can say the list is cut rather than implying these are the only slots that exist.

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
limit = 50 # object | Maximum number of items to return on this page. (optional) (default to 50)

try:
    # List this agent's attribute registry
    api_response = api_instance.list_attributes_endpoint_agents_agent_id_claims_attributes_get(agent_id, q=q, limit=limit)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->list_attributes_endpoint_agents_agent_id_claims_attributes_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **q** | [**object**](.md)|  | [optional]
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 50]

### Return type

[**AttributeListResponse**](AttributeListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_entity_aliases_endpoint_agents_agent_id_claims_entities_entity_id_aliases_get**
> EntityAliasesResponse list_entity_aliases_endpoint_agents_agent_id_claims_entities_entity_id_aliases_get(agent_id, entity_id)

List aliases for an entity

Every surface form linked to this entity (active and inactive), newest first, whether it was authored here or observed during ingest. Used by the curation console so a reviewer can see which names already fold onto the entity before authoring another. A form is active when it binds: one that is awaiting corroboration, that a second entity already holds, or that has been withdrawn is listed inactive, and `status` says which of those it is. Bounded to the most recent forms rather than paginated.

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

# **list_entity_merges_endpoint_agents_agent_id_claims_entity_merges_get**
> EntityMergesResponse list_entity_merges_endpoint_agents_agent_id_claims_entity_merges_get(agent_id)

List entity merge edges

Every assertion that two entities are the same thing, newest first, active and withdrawn alike, each naming both entities and the run that proposed it. A withdrawn edge is kept rather than deleted, because the closures it caused are recorded against it.

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
    # List entity merge edges
    api_response = api_instance.list_entity_merges_endpoint_agents_agent_id_claims_entity_merges_get(agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->list_entity_merges_endpoint_agents_agent_id_claims_entity_merges_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

[**EntityMergesResponse**](EntityMergesResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_erasures_endpoint_agents_agent_id_claims_erasures_get**
> ErasureListResponse list_erasures_endpoint_agents_agent_id_claims_erasures_get(agent_id, limit=limit, cursor=cursor)

List this agent's erasure receipts

Every claim-layer erasure performed for this agent, newest first, so the question \"what have we erased\" can be answered without knowing each entity in advance. Reads the same ledger the erasure writes; issues no erasure of its own.

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
limit = 25 # object | Maximum number of items to return on this page. (optional) (default to 25)
cursor = NULL # object | Opaque pagination token from the previous response's `next_cursor`. Pass it back unchanged; omit it to start again from the first page. (optional)

try:
    # List this agent's erasure receipts
    api_response = api_instance.list_erasures_endpoint_agents_agent_id_claims_erasures_get(agent_id, limit=limit, cursor=cursor)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->list_erasures_endpoint_agents_agent_id_claims_erasures_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 25]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]

### Return type

[**ErasureListResponse**](ErasureListResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_quarantine_queue_endpoint_org_claims_quarantine_get**
> QuarantineQueueResponse list_quarantine_queue_endpoint_org_claims_quarantine_get(limit=limit, cursor=cursor, agent_id=agent_id)

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
agent_id = NULL # object | List only this agent's rows. An agent the caller cannot see, or one with nothing queued, returns the same empty page. A cursor is valid only with the filter it was issued under. (optional)

try:
    # List quarantined claims across the tenant
    api_response = api_instance.list_quarantine_queue_endpoint_org_claims_quarantine_get(limit=limit, cursor=cursor, agent_id=agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->list_quarantine_queue_endpoint_org_claims_quarantine_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 50]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]
 **agent_id** | [**object**](.md)| List only this agent&#x27;s rows. An agent the caller cannot see, or one with nothing queued, returns the same empty page. A cursor is valid only with the filter it was issued under. | [optional]

### Return type

[**QuarantineQueueResponse**](QuarantineQueueResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_split_proposal_queue_endpoint_org_claims_split_proposals_get**
> SplitProposalQueueResponse list_split_proposal_queue_endpoint_org_claims_split_proposals_get(limit=limit, cursor=cursor, agent_id=agent_id)

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
agent_id = NULL # object | List only this agent's rows. An agent the caller cannot see, or one with nothing queued, returns the same empty page. A cursor is valid only with the filter it was issued under. (optional)

try:
    # List open split proposals across the tenant
    api_response = api_instance.list_split_proposal_queue_endpoint_org_claims_split_proposals_get(limit=limit, cursor=cursor, agent_id=agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->list_split_proposal_queue_endpoint_org_claims_split_proposals_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **limit** | [**object**](.md)| Maximum number of items to return on this page. | [optional] [default to 50]
 **cursor** | [**object**](.md)| Opaque pagination token from the previous response&#x27;s &#x60;next_cursor&#x60;. Pass it back unchanged; omit it to start again from the first page. | [optional]
 **agent_id** | [**object**](.md)| List only this agent&#x27;s rows. An agent the caller cannot see, or one with nothing queued, returns the same empty page. A cursor is valid only with the filter it was issued under. | [optional]

### Return type

[**SplitProposalQueueResponse**](SplitProposalQueueResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **plan_harness_repair_endpoint_agents_agent_id_claims_harness_repair_plan_get**
> HarnessRepairPlan plan_harness_repair_endpoint_agents_agent_id_claims_harness_repair_plan_get(agent_id)

Plan the repair of claims minted from harness text

Classify every entity in the agent's registry against the host's own markup vocabulary and report what an apply would erase, what it would leave, and the evidence for each. Reads only. An entity is erasable two ways, and a name alone is never one of them: every claim is harness-shaped, or the name is a host id and at least one claim corroborates it. An entity holding no claims is never erased, however it is named, and neither is one whose claims are all a customer's own. Each verdict carries its own `consent` token and the `etag` is the fold over all of them, which is the token for approving the whole list; approving a subset means folding that subset's tokens. Bounded, and `is_truncated` says when there was more. Refused for any agent not on the repair allowlist, named in code.

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
    # Plan the repair of claims minted from harness text
    api_response = api_instance.plan_harness_repair_endpoint_agents_agent_id_claims_harness_repair_plan_get(agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->plan_harness_repair_endpoint_agents_agent_id_claims_harness_repair_plan_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

[**HarnessRepairPlan**](HarnessRepairPlan.md)

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
if_match = NULL # object | The consent ETag returned by GET .../review-context. Required for release, promote, adopt and propose-split: it proves the reviewer saw this claim's state, and a stale token is refused. (optional)

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
 **if_match** | [**object**](.md)| The consent ETag returned by GET .../review-context. Required for release, promote, adopt and propose-split: it proves the reviewer saw this claim&#x27;s state, and a stale token is refused. | [optional]

### Return type

[**CuratedClaim**](CuratedClaim.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **propose_split_endpoint_agents_agent_id_claims_claim_id_propose_split_post**
> ClaimOpenSplit propose_split_endpoint_agents_agent_id_claims_claim_id_propose_split_post(body, agent_id, claim_id, if_match=if_match)

Propose a split so two true values can coexist

Open a split proposal on this claim's attribute so competing values can stay true under different qualifiers instead of superseding one another. Coalesces onto an already-open proposal for the key. Requires the If-Match consent token. The claim must be filed under an attribute.

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
body = hyperstruck.ProposeSplitRequest() # ProposeSplitRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.
claim_id = NULL # object | Claim UUID returned by a curation queue, dossier, or review-context endpoint.
if_match = NULL # object | The consent ETag returned by GET .../review-context. Required for release, promote, adopt and propose-split: it proves the reviewer saw this claim's state, and a stale token is refused. (optional)

try:
    # Propose a split so two true values can coexist
    api_response = api_instance.propose_split_endpoint_agents_agent_id_claims_claim_id_propose_split_post(body, agent_id, claim_id, if_match=if_match)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->propose_split_endpoint_agents_agent_id_claims_claim_id_propose_split_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ProposeSplitRequest**](ProposeSplitRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **claim_id** | [**object**](.md)| Claim UUID returned by a curation queue, dossier, or review-context endpoint. |
 **if_match** | [**object**](.md)| The consent ETag returned by GET .../review-context. Required for release, promote, adopt and propose-split: it proves the reviewer saw this claim&#x27;s state, and a stale token is refused. | [optional]

### Return type

[**ClaimOpenSplit**](ClaimOpenSplit.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **read_claims_for_question_endpoint_agents_agent_id_claims_question_post**
> QuestionClaimReadResponse read_claims_for_question_endpoint_agents_agent_id_claims_question_post(body, agent_id)

Answer a question from an agent's claims

Every claim this agent holds that bears on a question, across entities, as data. Unlike the recall path a turn uses, which caps its claim lane for prompt-injection reasons that are correct there, this read is not capped: it returns two arms with two different guarantees. The deterministic arm enumerates every claim on every entity the question's names reached, with a true total and deep stable paging, and says `exhaustive` when it managed that and `partial` when it did not. The recall arm is an approximate search, bounded and labelled `best_effort`. They are never blended into one total, because the checkable statement 'this is everything we hold about this account' is the product and an approximate scan cannot make it.  Read `deterministic.guarantee` and `is_total_exact` before quoting any number. Both sides of an unresolved contradiction are always returned and each names the other. Superseded values are excluded unless asked for; values that have merely gone stale are returned, marked. Rows held for human review are counted and never returned. Every row says how it was reached and where it was read from, and a row with no source says why it has none rather than arriving bare.  A POST because the question is free text of arbitrary length and the position is a structured token; it reads and writes nothing, records no run, and earns no attribution.

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
body = hyperstruck.QuestionClaimReadRequest() # QuestionClaimReadRequest |
agent_id = NULL # object | Hosted agent UUID returned by the agent create or list endpoint.

try:
    # Answer a question from an agent's claims
    api_response = api_instance.read_claims_for_question_endpoint_agents_agent_id_claims_question_post(body, agent_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->read_claims_for_question_endpoint_agents_agent_id_claims_question_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**QuestionClaimReadRequest**](QuestionClaimReadRequest.md)|  |
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |

### Return type

[**QuestionClaimReadResponse**](QuestionClaimReadResponse.md)

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
if_match = NULL # object | The consent ETag returned by GET .../review-context. Required for release, promote, adopt and propose-split: it proves the reviewer saw this claim's state, and a stale token is refused. (optional)

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
 **if_match** | [**object**](.md)| The consent ETag returned by GET .../review-context. Required for release, promote, adopt and propose-split: it proves the reviewer saw this claim&#x27;s state, and a stale token is refused. | [optional]

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

# **reverse_entity_merge_endpoint_agents_agent_id_claims_entity_merges_merge_id_reverse_post**
> EntityMergeReversalResponse reverse_entity_merge_endpoint_agents_agent_id_claims_entity_merges_merge_id_reverse_post(agent_id, merge_id)

Withdraw an entity merge

Withdraw an entity merge and reopen exactly the versions it closed, so two entities merged in error read as two again. Repairs beliefs, not actions.

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
merge_id = NULL # object | Entity merge edge UUID returned by the entity merge listing endpoint.

try:
    # Withdraw an entity merge
    api_response = api_instance.reverse_entity_merge_endpoint_agents_agent_id_claims_entity_merges_merge_id_reverse_post(agent_id, merge_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->reverse_entity_merge_endpoint_agents_agent_id_claims_entity_merges_merge_id_reverse_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **merge_id** | [**object**](.md)| Entity merge edge UUID returned by the entity merge listing endpoint. |

### Return type

[**EntityMergeReversalResponse**](EntityMergeReversalResponse.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **stored_answer_endpoint_agents_agent_id_answers_answer_id_get**
> AnswerView stored_answer_endpoint_agents_agent_id_answers_answer_id_get(agent_id, answer_id, detail=detail)

The same answer, at another level of detail

Returns an answer `POST /agents/{agent_id}/answer` gave, word for word, at the level `detail` names. Follow an answer's `more` links rather than building the path.  No model runs and nothing is billed. Answers are served for 30 days. Needs `claims:read` AND `agents:read`, the same as the answer itself.

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
answer_id = NULL # object | The `answer_id` an answer was given with, as its `more` links carry it.
detail = hyperstruck.AnswerDetail() # AnswerDetail |  (optional) (default to answer)

try:
    # The same answer, at another level of detail
    api_response = api_instance.stored_answer_endpoint_agents_agent_id_answers_answer_id_get(agent_id, answer_id, detail=detail)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ClaimsApi->stored_answer_endpoint_agents_agent_id_answers_answer_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_id** | [**object**](.md)| Hosted agent UUID returned by the agent create or list endpoint. |
 **answer_id** | [**object**](.md)| The &#x60;answer_id&#x60; an answer was given with, as its &#x60;more&#x60; links carry it. |
 **detail** | [**AnswerDetail**](.md)|  | [optional] [default to answer]

### Return type

[**AnswerView**](AnswerView.md)

### Authorization

[BearerApiKey](../README.md#BearerApiKey)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **wipe_agent_claims_endpoint_agents_agent_id_claims_delete**
> ClaimWipeResponse wipe_agent_claims_endpoint_agents_agent_id_claims_delete(agent_id, body=body)

Erase a batch of this agent's entities and their claim layer

Erase this agent's entities and their claims, aliases, dossiers and split proposals, writing one receipt per entity, and drop the agent's attribute vocabulary once the last entity is gone. Each entity goes through the same erasure as the single-entity route, so the reinforcement its claims granted is withdrawn before the delete and no rule keeps standing on erased evidence. **One request erases a bounded batch**: the erasure is serial, so an unbounded pass over a large corpus would outrun the request. `remaining_entities` says how many are left, and a non-zero count means call again. Repeating is safe either way, because each entity's erasure is idempotent, so a retry after a timeout resumes rather than starting over. Answers 503 when some entities in a batch were erased and others could not be; the receipts already written stand. Like the single erasure this is a claim-layer erasure, not a full Article 17 erasure: learnings, graph nodes, raw run traces and usage aggregates are not deleted, and each receipt names them. The reason and ticket reference are an optional body; a client or proxy that drops a DELETE body loses only that context, never the erasure.

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
    # Erase a batch of this agent's entities and their claim layer
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

