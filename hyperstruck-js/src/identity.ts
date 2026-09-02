/**
 * Who a run belongs to. Resolved once at seat construction, never from a run key.
 *
 * Tenancy rides entirely on the API key, with `org_id` resolved server-side. Deriving a
 * tenant from a correlation key would turn a missed inference into a cross-tenant leak
 * rather than a lost attribution, and those are not the same class of mistake.
 */
export interface AgentIdentity {
  /** The boundary agent name, not the hosted agent UUID. */
  readonly agentName: string;
  /** Optional explicit org, for a key that spans more than one. Usually omitted. */
  readonly orgId?: string | null;
}

export function identityPayload(identity: AgentIdentity): {
  agent_name: string;
  org_id: string | null;
} {
  return { agent_name: identity.agentName, org_id: identity.orgId ?? null };
}
