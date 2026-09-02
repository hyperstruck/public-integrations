# hyperstruck-sdk

Python client SDK for the Hyperstruck Core API.

This package is generated from the Hyperstruck OpenAPI document with [Swagger Codegen](https://github.com/swagger-api/swagger-codegen) using the `python` generator.

## Installation

```bash
python3 -m pip install hyperstruck-sdk
```

## Quick Start

```python
import os

import hyperstruck
from hyperstruck.rest import ApiException

api_key = os.environ["HYPER_API_KEY"]

configuration = hyperstruck.Configuration()
configuration.host = "https://api.hyperstruck.com"

api_client = hyperstruck.ApiClient(configuration)
api_client.set_default_header("Authorization", f"Bearer {api_key}")

agents_api = hyperstruck.AgentsApi(api_client)

try:
    agents = agents_api.list_agents_endpoint_agents_get(
        include_summary=False,
        limit=20,
    )
    print(agents)
except ApiException as exc:
    print(f"Hyperstruck API request failed: {exc}")
```

## Authentication

Hyperstruck API requests use bearer token authentication. Set the `Authorization` header on the generated `ApiClient`:

```python
api_client = hyperstruck.ApiClient(configuration)
api_client.set_default_header("Authorization", f"Bearer {api_key}")
```

## API Base URL

The recommended production API base URL is:

```text
https://api.hyperstruck.com
```

For local development, point the generated client at your local API:

```python
configuration = hyperstruck.Configuration()
configuration.host = "http://localhost:8000"
```

## Common APIs

```python
agents_api = hyperstruck.AgentsApi(api_client)
learnings_api = hyperstruck.LearningsApi(api_client)
plans_api = hyperstruck.PlansApi(api_client)
runs_api = hyperstruck.RunsApi(api_client)
sessions_api = hyperstruck.SessionsApi(api_client)
usage_api = hyperstruck.UsageApi(api_client)
```

The generated method names are derived from the OpenAPI operation IDs. For example:

- `AgentsApi.list_agents_endpoint_agents_get(...)`
- `AgentsApi.create_agent_endpoint_agents_post(...)`
- `RunsApi.get_run_endpoint_runs_run_id_get(...)`
- `LearningsApi.search_learnings_endpoint_agents_agent_id_learnings_search_get(...)`

## Regeneration Notes

This SDK was fully regenerated from the platform OpenAPI after the learnings
inventory search change. The regeneration also catches up earlier API contract
drift: provider-credential endpoints are no longer part of the public API, so
`ProviderCredentialsApi` is removed, and agent-list signatures no longer include
the retired `include_llm_credential` argument.

## Publishing

This SDK is intended to be published as:

```bash
python3 -m build
python3 -m twine upload dist/*
```

Repository maintainers should prefer the GitHub Actions publishing workflow from the monorepo so credentials stay in GitHub secrets and are never committed to `public_integrations/`.
