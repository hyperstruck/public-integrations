const { mkdtempSync, rmSync } = require("node:fs");
const { spawnSync } = require("node:child_process");
const { join } = require("node:path");

const projectDirectory = __dirname;
const outputDirectory = mkdtempSync(join(projectDirectory, ".boundary-test-"));

function run(command, args) {
  return (
    spawnSync(command, args, {
      cwd: projectDirectory,
      stdio: "inherit",
    }).status ?? 1
  );
}

let exitCode = 1;
try {
  exitCode = run(process.execPath, [
    require.resolve("typescript/bin/tsc"),
    "--outDir",
    outputDirectory,
    "--target",
    "es5",
    "--module",
    "commonjs",
    "--lib",
    "es6,dom",
    "--skipLibCheck",
    "custom.d.ts",
    "boundary_wire_contract.spec.ts",
  ]);
  if (exitCode === 0) {
    // The spec declares describe/test/expect as ambient, which emits nothing to JavaScript, so
    // the compiled file calls globals that only this runner supplies. Defining them here is what
    // makes those declarations true; without it the spec throws ReferenceError on its first line
    // and the wire assertions it exists for never run.
    exitCode = run(process.execPath, [
      "--require",
      join(projectDirectory, "boundary_test_globals.cjs"),
      join(outputDirectory, "boundary_wire_contract.spec.js"),
    ]);
  }
} finally {
  rmSync(outputDirectory, { recursive: true, force: true });
}

process.exitCode = exitCode;
