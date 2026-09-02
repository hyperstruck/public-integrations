/**
 * A search of a hosted agent's claims, as the platform publishes it.
 *
 * A search is a read: the claims nearest the question, written out as `text` by code, with the
 * same claims beside it as `claims`. Nothing is stored or billed, so searching again is always safe.
 */
import type { components } from "./schema.ts";

export type ClaimSearch = components["schemas"]["ClaimSearchOut"];
export type ClaimSearchDetail = components["schemas"]["ClaimSearchIn"]["detail"];
export type ClaimSearchState = NonNullable<components["schemas"]["ClaimSearchIn"]["state"]>;
export type ClaimSearchKind = NonNullable<components["schemas"]["ClaimSearchIn"]["kind"]>;
