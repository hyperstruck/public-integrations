# @hyperstruck/sdk

TypeScript client SDK for the Hyperstruck Core API.

This package is generated from the Hyperstruck OpenAPI document with [Swagger Codegen](https://github.com/swagger-api/swagger-codegen) using the `typescript-fetch` generator.

For agent learning in Python (LangGraph middleware, IDE hooks, and bundled skills), use the hand-written [`hyperstruck-py`](../../hyperstruck-py/) package. Reach for this SDK when you need raw, fully typed access to every API endpoint from TypeScript.

## Installation

```bash
npm i @hyperstruck/sdk
```

## Quick Start

```typescript
import { AgentsApi, Configuration } from "@hyperstruck/sdk";

const apiKey = process.env.HYPER_API_KEY;

if (!apiKey) {
  throw new Error("HYPER_API_KEY is required");
}

const configuration = new Configuration({
  basePath: "https://api.hyperstruck.com",
});

const agentsApi = new AgentsApi(configuration);

const agents = await agentsApi.listAgentsEndpointAgentsGet(
  false,
  20,
  undefined,
  {
    headers: {
      Authorization: `Bearer ${apiKey}`,
    },
  },
);

console.log(agents);
```

## Authentication

Hyperstruck API requests use bearer token authentication:

```typescript
const authOptions = {
  headers: {
    Authorization: `Bearer ${process.env.HYPER_API_KEY}`,
  },
};
```

Pass the options object as the final argument to generated API methods.

## API Base URL

The recommended production API base URL is:

```text
https://api.hyperstruck.com
```

For local development, point the generated client at your local API:

```typescript
const configuration = new Configuration({
  basePath: "http://localhost:8000",
});
```

## Common APIs

```typescript
import {
  AgentsApi,
  LearningsApi,
  PlansApi,
  ProviderCredentialsApi,
  RunsApi,
  SessionsApi,
  UsageApi,
  Configuration,
} from "@hyperstruck/sdk";
```

The generated method names are derived from the OpenAPI operation IDs. For example:

- `AgentsApi.listAgentsEndpointAgentsGet(...)`
- `AgentsApi.createAgentEndpointAgentsPost(...)`
- `RunsApi.getRunEndpointRunsRunIdGet(...)`
- `LearningsApi.searchLearningsEndpointAgentsAgentIdLearningsSearchGet(...)`

## Publishing

This SDK is intended to be published as:

```bash
cd public_integrations/sdk/typescript
npm install
npm run build
npm publish --dry-run --access public
npm publish --access public
```

Repository maintainers should prefer the GitHub Actions publishing workflow from the monorepo so credentials stay in GitHub secrets and are never committed to `public_integrations/`.
