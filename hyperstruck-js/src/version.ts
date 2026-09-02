/**
 * The version this client reports in its User-Agent.
 *
 * Read as a literal rather than out of `package.json`, because the boundary's receipt
 * gate parses this exact string out of the stored header and the two must move in one
 * commit. Importing the manifest would put the number behind a JSON resolution that
 * differs between the published build and the source tree, and a version that reads
 * correctly in tests and wrongly in the wheel is the one shape this cannot have.
 *
 * A parity test asserts this matches `package.json`, so the duplication is pinned rather
 * than trusted.
 */
export const VERSION = "0.12.0";

/** The User-Agent product token. Not the package name: an npm scope contains a solidus,
 * which is what separates product from version in a User-Agent, so `@hyperstruck/core`
 * ships under `hyperstruck-js`. The boundary's `RECEIPT_CAPABLE_CLIENTS` keys on it. */
export const CLIENT_PRODUCT = "hyperstruck-js";
