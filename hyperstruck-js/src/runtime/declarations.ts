/**
 * What a tool's values are, declared once by origin rather than guessed per value.
 *
 * A seat that assembles the episode automatically has to fill `declared_sensitivity`,
 * which until now was the caller's job and which no foreign caller has ever managed. The
 * mechanism here is per-tool declaration with propagation: a tool is declared once, and
 * every value flowing out of it inherits the label.
 *
 * **Origin, not inspection.** This is the design the Engine's own executor already runs
 * internally, stamping the same field from the tool schema, and it is what the
 * capability-tracking research argues for. CaMeL labels every value with provenance as it
 * flows through tool calls and enforces at the tool boundary rather than detecting
 * sensitivity in content. Content inspection is a heuristic that fails open; provenance
 * is exact.
 *
 * **The unit is the step, not the value, and the reason is decisive.** The dynamic taint
 * analysis literature names taint explosion as what happens when propagation is
 * indiscriminate: nearly everything ends up tainted and the analysis stops meaning
 * anything, which is why DTA++ propagates along a targeted subset instead. And we could
 * not do it soundly from here anyway. CaMeL gets its precision from a custom interpreter
 * over a plan it controls, with a real data-flow graph; we sit at a hook and see tool
 * inputs and outputs, with the customer's code that moved data between them invisible to
 * us. A label that is trusted and wrong is worse than one that is coarse and known to be.
 *
 * **One bounded refinement, because it is observable from where we sit.** Where a later
 * tool's argument literally contains a value that appeared in an earlier tool's output in
 * the same run, the labels join. Checked one hop against the run's recorded outputs,
 * never transitively, and it can only escalate.
 */

/** The producer labels the boundary reads, most restrictive first. Anything else is
 * treated as declaring nothing, exactly as the server treats an unrecognised tool
 * category: a guess is indistinguishable from silence while looking like a declaration. */
export const SECRET = "secret";
export const USER_DATA = "user_data";
export const SHAREABLE = "shareable";

const ORDER = [SECRET, USER_DATA, SHAREABLE] as const;
const RANK = new Map<string, number>(ORDER.map((label, index) => [label, index]));

/**
 * What an undeclared argument is treated as. The most restrictive member, deliberately: a
 * tool nobody described could be returning anything, and the failure directions are not
 * symmetric. Over-restricting costs the corpus a value and is visible in the run report;
 * under-restricting egresses a customer's data and is visible nowhere.
 */
export const UNDECLARED_SENSITIVITY = SECRET;

/** The JSON Schema annotation naming the subject argument, and the role values that
 * count. Copied from Core's reader rather than imported, because the neutral client may
 * not load the engine; the values are pinned by the parity tests over this wire. */
export const SUBJECT_ROLE_KEY = "role";
export const SUBJECT_ROLE_VALUES: ReadonlySet<string> = new Set([
  "entity",
  "subject",
  "resource",
]);

/** The wire key Core reads the subject declaration from. */
export const SUBJECT_KEY = "subject";

/**
 * The shortest output value the one-hop join will match on. A two-character value appears
 * by coincidence in almost any later argument, and every coincidence is an escalation that
 * withholds something the customer wanted, so the floor is the same discipline the
 * redaction scrub applies for the same reason.
 */
export const MIN_PROPAGATED_VALUE_LENGTH = 6;

/**
 * How many values one step's output contributes to the join. A tool returning a thousand
 * rows would otherwise make the next call's check quadratic on the close path, and the
 * hundredth value from one result adds nothing the first few did not: the case this catches
 * is an agent copying a field out of a result into the next call, not a bulk transfer.
 */
export const MAX_PROPAGATED_VALUES_PER_STEP = 32;

/**
 * Bounded so a cyclic or pathologically nested tool result cannot turn the join table into
 * a hang on the close path. Matches the receipt flattener's own bound for the same reason.
 */
const MAX_RESULT_DEPTH = 8;

function* stringsIn(
  value: unknown,
  depth = 0,
  seen: Set<object> = new Set(),
): Generator<string> {
  if (depth > MAX_RESULT_DEPTH) return;
  if (typeof value === "string") {
    if (value) yield value;
    return;
  }
  if (value === null || typeof value !== "object") return;
  if (seen.has(value)) return;
  seen.add(value);
  const items = Array.isArray(value)
    ? value
    : Object.values(value as Record<string, unknown>);
  for (const item of items) yield* stringsIn(item, depth + 1, seen);
}

/**
 * The more restrictive of two labels. Escalate only, never lower.
 *
 * Origin declaration and a content scan can both be active on the same value and can
 * disagree, and this is the rule for that too: a scan may raise a value's sensitivity
 * above what its tool declared and may never lower it. A tool declared permissively whose
 * output turns out to carry personal data is the case the net exists for; a tool declared
 * restrictively whose content looks innocuous is not evidence the declaration was wrong.
 */
/**
 * One of the three labels the boundary reads, or `null`.
 *
 * Anything else declares nothing, which is how the server treats an unrecognised producer
 * label. Normalising here rather than trusting the caller matters more than it looks: an
 * unrecognised label used to score rank 0 in {@link join}, tie with `secret`, and win the
 * tie, so a tool declared `{a: "Secret", b: "secret"}` propagated `"Secret"` onward. That
 * reads as maximally restrictive locally and as *no declaration* at the boundary, so the
 * one function whose contract is "escalate only, never lower" was lowering.
 */
export function canonical(label: string | null | undefined): string | null {
  if (typeof label !== "string") return null;
  const normalised = label.trim().toLowerCase();
  return RANK.has(normalised) ? normalised : null;
}

export function join(left: string | null, right: string | null): string | null {
  const a = canonical(left);
  const b = canonical(right);
  if (a === null) return b;
  if (b === null) return a;
  // Both canonical here, so the lookup cannot fall back and a tie means one string.
  return (RANK.get(a) as number) <= (RANK.get(b) as number) ? a : b;
}

function isSubjectField(schema: Record<string, unknown>): boolean {
  const role = schema[SUBJECT_ROLE_KEY];
  if (typeof role === "string" && SUBJECT_ROLE_VALUES.has(role.toLowerCase())) return true;
  return schema["in"] === "path";
}

/**
 * The single argument a tool's schema declares as its subject entity, or `null`.
 *
 * `null` when zero or more than one parameter is declared the subject: an ambiguous
 * declaration is treated as no declaration, so a clean single declaration is
 * authoritative and everything else falls to Core's structural resolution. The OpenAPI
 * `in: "path"` convention counts as an implicit subject, since a REST path parameter is
 * conventionally the resource identifier.
 */
export function subjectArgKey(
  parameters: Record<string, unknown> | null | undefined,
): string | null {
  if (!parameters) return null;
  const declaredProperties = parameters["properties"];
  const properties =
    declaredProperties !== null &&
    typeof declaredProperties === "object" &&
    !Array.isArray(declaredProperties)
      ? (declaredProperties as Record<string, unknown>)
      : parameters;
  const subjects = Object.entries(properties)
    .filter(
      ([, schema]) =>
        schema !== null &&
        typeof schema === "object" &&
        !Array.isArray(schema) &&
        isSubjectField(schema as Record<string, unknown>),
    )
    .map(([key]) => key);
  return subjects.length === 1 ? (subjects[0] as string) : null;
}

/**
 * One tool, described once, by whoever knows what it returns.
 *
 * `args` maps argument name to label. `subject` names the argument carrying the entity
 * the result is about and is deliberately not part of the sensitivity story: it is a
 * different question with a different default, and conflating them is what the trap in
 * the default below is about.
 */
export interface ToolDeclaration {
  readonly name: string;
  readonly args?: Readonly<Record<string, string>>;
  readonly subject?: string | null;
}

/**
 * Read what the tool's own schema already says, and take the rest as given.
 *
 * The subject comes free for a customer who annotates their schema, which is the point:
 * the declaration they already wrote for their own API documentation is the one Core
 * reads.
 */
export function declarationFromSchema(
  name: string,
  parameters: Record<string, unknown> | null | undefined,
  args?: Readonly<Record<string, string>>,
): ToolDeclaration {
  return { name, args: { ...(args ?? {}) }, subject: subjectArgKey(parameters) };
}

/**
 * The `declared_sensitivity` stamp for one step.
 *
 * A section whose value is a bare string carries a single declaration, of which
 * `subject` is the one the runtime reads. The index signature is deliberately not
 * optional-valued: an explicit `undefined` would serialise as an absent key on some
 * paths and as a JSON null on others, and the published clients cannot transmit a JSON
 * null in either direction, so a key is either present with a value or is not there.
 */
export type DeclarationStamp = Record<string, Record<string, string> | string>;

/**
 * Every tool's declaration, and what a run withheld for want of one.
 *
 * **The trap in the default, said out loud.** Undeclared means most restrictive, and a
 * silent restrictive default is a trap we have already sprung on this exact customer: a
 * run wrote claims, no rule reported anything, and they read it as the product being
 * broken. So this registry never withholds silently. Every run reports how many fields
 * went undeclared, which tools they came from, and the configuration that releases them,
 * which is the same discipline as the `resolve_empty` versus `resolve_failed` taxonomy. A
 * configuration state must never look like a broken product.
 *
 * **The default governs sensitivity only and explicitly not the subject key.** An
 * undeclared subject falls through to Core's structural salience rung, which is today's
 * behaviour. Applying "most restrictive" there would withhold a fact whenever its subject
 * argument was undeclared, which would defeat the subject fix shipping in the same change
 * and be strictly worse than today.
 */
export class DeclarationRegistry {
  private readonly byName = new Map<string, ToolDeclaration>();
  private readonly isUndeclaredRestricted: boolean;

  constructor(
    declarations: Iterable<ToolDeclaration> = [],
    options: { isUndeclaredRestricted?: boolean } = {},
  ) {
    for (const declaration of declarations) this.byName.set(declaration.name, declaration);
    this.isUndeclaredRestricted = options.isUndeclaredRestricted ?? true;
  }

  register(declaration: ToolDeclaration): void {
    this.byName.set(declaration.name, declaration);
  }

  /** Read declarations off a roster of tool specs that carry schemas. */
  registerTools(
    tools: Iterable<{ name?: string; parameters?: Record<string, unknown> | null }>,
  ): void {
    for (const tool of tools) {
      const name = tool.name;
      if (!name || this.byName.has(name)) continue;
      const declaration = declarationFromSchema(name, tool.parameters);
      if (declaration.subject) this.byName.set(name, declaration);
    }
  }

  /**
   * The `declared_sensitivity` stamp for one step, and what it withheld.
   *
   * The second element is not diagnostics dressing. It is the mechanism by which a
   * restrictive default stays legible: it names the tool, what was withheld, and the one
   * thing the customer can do about it.
   */
  declarationFor(
    toolName: string,
    args?: Readonly<Record<string, unknown>> | null,
  ): { stamp: DeclarationStamp | null; withheld: string[] } {
    const declaration = this.byName.get(toolName);
    const stamp: Record<string, Record<string, string> | string> = {};
    const withheld: string[] = [];

    const declaredArgs: Record<string, string> = { ...(declaration?.args ?? {}) };
    if (args && this.isUndeclaredRestricted) {
      // `hasOwnProperty`, not `in`. The `in` operator walks the prototype chain, so an
      // argument named `toString`, `constructor`, `valueOf` or `__proto__` reported as
      // already declared, was never stamped with the restrictive default, produced no
      // withheld line, and was released silently. Python's `not in` on a dict is exact,
      // so this was a hole in one language only, in the default the whole propagation
      // design rests on.
      const undeclared = Object.keys(args).filter(
        (key) => !Object.prototype.hasOwnProperty.call(declaredArgs, key),
      );
      for (const key of undeclared) declaredArgs[key] = UNDECLARED_SENSITIVITY;
      if (undeclared.length > 0) {
        withheld.push(
          `${toolName}: ${undeclared.length} undeclared argument(s) ` +
            `(${[...undeclared].sort().join(", ")}) withheld as ${UNDECLARED_SENSITIVITY}; ` +
            "declare the tool, or construct the registry with " +
            "isUndeclaredRestricted: false, to release them",
        );
      }
    }
    if (Object.keys(declaredArgs).length > 0) stamp["args"] = declaredArgs;
    // Bare string rather than a nested object, which is the shape the boundary accepts
    // and the one Core's subject resolver reads. The published clients' own types were
    // the last thing stopping it being sent.
    if (declaration?.subject) stamp[SUBJECT_KEY] = declaration.subject;
    return {
      stamp: Object.keys(stamp).length > 0 ? stamp : null,
      withheld,
    };
  }

  /**
   * Whether every tool the run used carries a declaration.
   *
   * Gates cross-tenant org promotion: an undeclared or empty-declared foreign tool keeps
   * the run's learnings agent-private. A run with no tool calls has nothing foreign to
   * gate.
   */
  isFullyDeclared(toolNames: Iterable<string>): boolean {
    const names = new Set(toolNames);
    if (names.size === 0) return true;
    for (const name of names) {
      const declaration = this.byName.get(name);
      if (declaration === undefined) return false;
      if (Object.keys(declaration.args ?? {}).length === 0) return false;
    }
    return true;
  }

  /**
   * The label a tool's own output carries, joined over what it declared.
   *
   * `null` for a tool that declared nothing, deliberately, and this is the decisive
   * default in the other direction from the argument one. Treating an undeclared tool's
   * output as most restrictive would taint every later argument that quoted it, which is
   * taint explosion by another route: a label that is always the most restrictive one is
   * the same as no label, and here it would mean withholding everything and telling the
   * customer their corpus is empty.
   */
  outputLabel(toolName: string): string | null {
    const declaration = this.byName.get(toolName);
    const args = declaration?.args ?? {};
    if (Object.keys(args).length === 0) return null;
    let label: string | null = null;
    for (const value of Object.values(args)) label = join(label, value);
    return label;
  }

  /**
   * Add one step's output values to the run's join table, in place.
   *
   * Bounded in both directions: a value shorter than
   * {@link MIN_PROPAGATED_VALUE_LENGTH} is skipped because it matches by coincidence, and
   * at most {@link MAX_PROPAGATED_VALUES_PER_STEP} values are taken from one result
   * because the check is against every later argument and the case this exists for is a
   * field copied across, not a bulk transfer.
   *
   * A tool that declared nothing contributes nothing, so an undeclared tool cannot
   * escalate anything through this route.
   */
  recordOutputs(priorOutputs: Map<string, string>, toolName: string, result: unknown): void {
    const label = this.outputLabel(toolName);
    if (label === null) return;
    let taken = 0;
    for (const value of stringsIn(result)) {
      if (taken >= MAX_PROPAGATED_VALUES_PER_STEP) return;
      if (value.length < MIN_PROPAGATED_VALUE_LENGTH) continue;
      priorOutputs.set(value, join(priorOutputs.get(value) ?? null, label) ?? label);
      taken += 1;
    }
  }

  /**
   * The one-hop join: a value copied out of an earlier result keeps its label.
   *
   * `priorOutputs` maps a value seen in an earlier step's output to that step's label. A
   * later argument that literally contains one of those values joins its label. One hop
   * against this run's recorded outputs, never transitively, and it can only escalate.
   */
  propagate(
    toolName: string,
    args: Readonly<Record<string, unknown>>,
    priorOutputs: ReadonlyMap<string, string>,
  ): Record<string, string> {
    const escalated: Record<string, string> = {};
    if (priorOutputs.size === 0) return escalated;
    const declared = this.byName.get(toolName)?.args ?? {};
    for (const [key, value] of Object.entries(args)) {
      if (typeof value !== "string" || value.length === 0) continue;
      let inherited: string | null = null;
      for (const [seen, label] of priorOutputs) {
        if (seen && value.includes(seen)) inherited = join(inherited, label);
      }
      const base = declared[key] ?? null;
      const joined = join(base, inherited);
      if (joined !== null && joined !== base) escalated[key] = joined;
    }
    return escalated;
  }
}
