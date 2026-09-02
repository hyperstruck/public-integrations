import assert from "node:assert/strict";
import { test } from "node:test";

import {
  DELIVERED_REFORMATTED,
  DELIVERED_VERBATIM,
  flattenParams,
  locateReceipt,
  receiptOutcome,
  UNRESOLVED,
} from "./receipt.ts";

const ADVICE = "- always check the invoice currency\n- confirm the party before writing";

test("a block that arrived intact is graded verbatim", () => {
  const sent = `You are helpful.\n${ADVICE}\nUser: go`;
  const located = locateReceipt(sent, [
    { name: "advice", text: ADVICE, offeredIds: ["a1", "a2"] },
  ]);
  assert.equal(located.shelves[0]?.outcome, DELIVERED_VERBATIM);
  assert.equal(receiptOutcome(located), DELIVERED_VERBATIM);
});

test("a host that renumbered the bullets is a delivery, not a drop", () => {
  const sent =
    "You are helpful.\n1. always check the invoice currency\n2. confirm the party before writing";
  const located = locateReceipt(sent, [
    { name: "advice", text: ADVICE, offeredIds: ["a1", "a2"] },
  ]);
  assert.equal(located.shelves[0]?.outcome, DELIVERED_REFORMATTED);
  assert.equal(located.shelves[0]?.linesFound, 2);
});

test("a block that never arrived yields no receipt rather than an empty one", () => {
  const located = locateReceipt("nothing of ours here", [
    { name: "advice", text: ADVICE, offeredIds: ["a1"] },
  ]);
  assert.equal(located.text, null);
  assert.equal(located.shelves[0]?.outcome, UNRESOLVED);
});

test("a trimming layer that dropped a line shows as missing rather than as delivered", () => {
  const sent = "You are helpful.\n- always check the invoice currency";
  const located = locateReceipt(sent, [
    { name: "advice", text: ADVICE, offeredIds: ["a1", "a2"] },
  ]);
  assert.equal(located.shelves[0]?.outcome, DELIVERED_REFORMATTED);
  assert.deepEqual(located.shelves[0]?.missingLines, [
    "confirm the party before writing",
  ]);
});

test("the receipt carries only lines we authored, never the content between two matches", () => {
  const sent = [
    "always check the invoice currency",
    "PATIENT: Jane Doe, card 4111111111111111, password hunter2",
    "confirm the party before writing",
  ].join("\n");
  const located = locateReceipt(sent, [
    { name: "advice", text: ADVICE, offeredIds: ["a1", "a2"] },
  ]);
  assert.ok(located.text !== null);
  assert.ok(!located.text.includes("PATIENT"));
  assert.ok(!located.text.includes("4111111111111111"));
  assert.ok(!located.text.includes("hunter2"));
});

test("a model echoing one of our lines elsewhere does not credit the shelf", () => {
  // One line of ours in a tool result, far from any block of ours, and nothing else.
  const filler = Array.from({ length: 30 }, (_, index) => `chatter ${index}`);
  const sent = [
    ...filler,
    "as you told me, always check the invoice currency",
    ...filler,
  ].join("\n");
  const located = locateReceipt(sent, [
    { name: "advice", text: ADVICE, offeredIds: ["a1", "a2"] },
  ]);
  // The echo is not a marker-stripped exact match of our line, so nothing is found.
  assert.equal(located.shelves[0]?.linesFound, 0);
  assert.equal(located.shelves[0]?.outcome, UNRESOLVED);
});

test("the richest cluster wins over one that merely repeats a single line", () => {
  const noise = Array.from({ length: 20 }, () => "always check the invoice currency");
  const sent = [...noise, ...Array.from({ length: 20 }, (_, i) => `gap ${i}`), ADVICE].join(
    "\n",
  );
  const located = locateReceipt(sent, [
    { name: "advice", text: ADVICE, offeredIds: ["a1", "a2"] },
  ]);
  assert.equal(located.shelves[0]?.linesFound, 2);
});

test("the run's outcome is the worst any shelf reported", () => {
  const facts = "Northwind Clinics Pty Ltd is registered in Victoria";
  const sent = `${ADVICE}\nUser: go`;
  const located = locateReceipt(sent, [
    { name: "advice", text: ADVICE, offeredIds: ["a1"] },
    { name: "facts", text: facts, offeredIds: ["f1"] },
  ]);
  assert.equal(located.shelves[0]?.outcome, DELIVERED_VERBATIM);
  assert.equal(located.shelves[1]?.outcome, UNRESOLVED);
  assert.equal(receiptOutcome(located), UNRESOLVED);
});

test("a shelf that offered nothing does not drag the run's outcome down", () => {
  const sent = `${ADVICE}\nUser: go`;
  const located = locateReceipt(sent, [
    { name: "advice", text: ADVICE, offeredIds: ["a1"] },
    { name: "obligations", text: null, offeredIds: [] },
  ]);
  assert.equal(receiptOutcome(located), DELIVERED_VERBATIM);
});

test("a continuation line beginning with a minus sign is not eaten by the marker stripper", () => {
  const block = "- range = -5 to -10 is out of bounds";
  const located = locateReceipt(`system\n${block}`, [
    { name: "advice", text: block, offeredIds: ["a1"] },
  ]);
  assert.equal(located.shelves[0]?.outcome, DELIVERED_VERBATIM);
});

test("flattening walks a nested params object and stops at a cycle", () => {
  const cyclic: Record<string, unknown> = { text: "hello" };
  cyclic["self"] = cyclic;
  const flattened = flattenParams({ prompt: [cyclic, { content: [{ text: "world" }] }] });
  assert.ok(flattened.includes("hello"));
  assert.ok(flattened.includes("world"));
});
