// The globals boundary_wire_contract.spec.ts declares as ambient. Kept beside the runner rather
// than inlined into the spec, because the spec is regenerated and this is not.
const assert = require("node:assert/strict");

const failures = [];
let ran = 0;
let suite = "";

globalThis.describe = (name, fn) => {
  suite = name;
  fn();
  suite = "";
};

globalThis.test = (name, fn) => {
  ran += 1;
  try {
    const result = fn();
    // An async body would resolve after this runner has already exited, so its assertions would
    // never be observed and the suite would pass on having run nothing. Refuse rather than
    // silently skip: this shim exists because assertions that did not execute looked green.
    if (result && typeof result.then === "function") {
      failures.push(`${suite} > ${name}: async test bodies are not supported by this runner`);
    }
  } catch (error) {
    failures.push(`${suite} > ${name}: ${error.message}`);
  }
};

globalThis.expect = (actual) => ({
  toBe(expected) {
    assert.strictEqual(actual, expected);
  },
  toBeUndefined() {
    assert.strictEqual(actual, undefined);
  },
});

process.on("exit", () => {
  for (const failure of failures) {
    console.error(failure);
  }
  // Zero tests is a failure, not a pass. A compiled spec whose describe block never ran, or a
  // generator that emitted no tests at all, is exactly the state this runner was restored to
  // catch, and it is indistinguishable from success by exit code alone.
  if (ran === 0) {
    console.error("no tests ran");
  }
  if (failures.length > 0 || ran === 0) {
    process.exitCode = 1;
  }
});
