"""What a tool's values are, declared once by origin rather than guessed per value.

A seat that assembles the episode automatically has to fill ``declared_sensitivity``, which
until now was the caller's job and which no foreign caller has ever managed. The mechanism
here is per-tool declaration with propagation: a tool is declared once, and every value
flowing out of it inherits the label.

**Origin, not inspection.** This is the design the Engine's own executor already runs
internally, stamping ``declared_sensitivity`` from the tool schema, and it is what the
capability-tracking research argues for. CaMeL labels every value with provenance as it
flows through tool calls and enforces at the tool boundary rather than detecting
sensitivity in content. Content inspection is a heuristic that fails open; provenance is
exact.

**The unit is the step, not the value, and the reason is decisive.** The dynamic taint
analysis literature names taint explosion as what happens when propagation is
indiscriminate: nearly everything ends up tainted and the analysis stops meaning anything,
which is why DTA++ propagates along a targeted subset instead. And we could not do it
soundly from here anyway. CaMeL gets its precision from a custom interpreter over a plan it
controls, with a real data-flow graph; we sit at a hook and see tool inputs and outputs,
with the customer's code that moved data between them invisible to us. A label that is
trusted and wrong is worse than one that is coarse and known to be.

**One bounded refinement, because it is observable from where we sit.** Where a later
tool's argument literally contains a value that appeared in an earlier tool's output in the
same run, the labels join. Checked one hop against the run's recorded outputs, never
transitively, and it can only escalate. That catches an agent copying a field out of one
result into the next call, which is the common real case, and the one-hop bound is the same
discipline and the same reason.

**CL36 rides the same registry.** ``declared_sensitivity["subject"]`` names which argument
carries the entity a step's result is about, and it is the top rung of Core's entity ladder,
outranking every salience-scored candidate. It is read from the tool's own JSON Schema
through the ``role`` annotation Core already reads, so a customer who annotates their schema
gets it with no second declaration. Losing that rung is what turned ``Northwind Clinics``
and ``Northwind Clinics Pty Ltd`` into two entities with separate dossiers in a real
customer's corpus, and a fragmented entity never accumulates corroboration and never reaches the stability the read side gates on.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

# The producer labels the boundary reads, most restrictive first. Anything else is treated
# as declaring nothing, exactly as the server treats an unrecognised tool category: a guess
# is indistinguishable from silence while looking like a declaration.
SECRET = "secret"
USER_DATA = "user_data"
SHAREABLE = "shareable"

# The lattice, most restrictive first. Used only to join, never to lower.
_ORDER = (SECRET, USER_DATA, SHAREABLE)
_RANK = {label: index for index, label in enumerate(_ORDER)}

# What an undeclared argument is treated as. The most restrictive member, deliberately: a
# tool nobody described could be returning anything, and the failure directions are not
# symmetric. Over-restricting costs the corpus a value and is visible in the run report;
# under-restricting egresses a customer's data and is visible nowhere.
UNDECLARED_SENSITIVITY = SECRET

# The JSON Schema annotation naming the subject argument, and the role values that count.
# Copied from Core's reader rather than imported, because the neutral client may not import
# the engine; the values are pinned by the parity tests that cover this wire.
SUBJECT_ROLE_KEY = "role"
SUBJECT_ROLE_VALUES = frozenset({"entity", "subject", "resource"})

# The wire key Core reads the subject declaration from.
SUBJECT_KEY = "subject"

# The shortest output value the one-hop join will match on. A two-character value appears
# by coincidence in almost any later argument, and every coincidence is an escalation that
# withholds something the customer wanted, so the floor is the same discipline the
# redaction scrub applies for the same reason.
MIN_PROPAGATED_VALUE_LENGTH = 6

# How many values one step's output contributes to the join. A tool returning a thousand
# rows would otherwise make the next call's check quadratic on the close path, and the
# hundredth value from one result adds nothing the first few did not: the case this catches
# is an agent copying a field out of a result into the next call, not a bulk transfer.
MAX_PROPAGATED_VALUES_PER_STEP = 32

# How many values the join table holds for a whole run. Bounded per step alone, a long run
# grows the table without limit and the check against it runs per argument per step, so the
# close path is quadratic in step count on exactly the runs that matter most. The oldest go
# first: the one-hop join is about a value copied from a recent result into the next call,
# so a value from fifty steps ago is not the case this exists for.
MAX_PROPAGATED_VALUES_PER_RUN = 512


def canonical(label: str | None) -> str | None:
    """One of the three labels the boundary reads, or ``None``.

    Anything else is treated as declaring nothing, which is how the server treats an
    unrecognised producer label and an unrecognised tool category alike. Normalising here
    rather than trusting the caller matters more than it looks: an unrecognised label used
    to score rank 0 in :func:`join`, tie with ``secret``, and win the tie, so a tool
    declared ``{"a": "Secret", "b": "secret"}`` propagated ``"Secret"`` onward. That reads
    as maximally restrictive locally and as *no declaration* at the boundary, so the one
    function whose docstring says "escalate only, never lower" was lowering.
    """
    if label is None:
        return None
    normalised = label.strip().lower()
    return normalised if normalised in _RANK else None


def join(left: str | None, right: str | None) -> str | None:
    """The more restrictive of two labels. Escalate only, never lower.

    Origin declaration and a content scan can both be active on the same value and can
    disagree, and this is the rule for that too: a scan may raise a value's sensitivity
    above what its tool declared and may never lower it. A tool declared permissively whose
    output turns out to carry personal data is the case the net exists for; a tool declared
    restrictively whose content looks innocuous is not evidence the declaration was wrong.
    """
    left = canonical(left)
    right = canonical(right)
    if left is None:
        return right
    if right is None:
        return left
    # Both are canonical here, so the rank lookup cannot fall back and a tie means the two
    # labels are the same string.
    return left if _RANK[left] <= _RANK[right] else right


def subject_arg_key(parameters: Mapping[str, Any] | None) -> str | None:
    """The single argument a tool's schema declares as its subject entity, or ``None``.

    ``None`` when zero or more than one parameter is declared the subject: an ambiguous
    declaration is treated as no declaration, so a clean single declaration is authoritative
    and everything else falls to Core's structural resolution. The OpenAPI ``in: "path"``
    convention counts as an implicit subject, since a REST path parameter is conventionally
    the resource identifier.
    """
    if not parameters:
        return None
    properties = parameters.get("properties")
    if not isinstance(properties, Mapping):
        properties = parameters
    subjects = [
        str(key)
        for key, schema in properties.items()
        if isinstance(schema, Mapping) and _is_subject_field(schema)
    ]
    return subjects[0] if len(subjects) == 1 else None


def _is_subject_field(schema: Mapping[str, Any]) -> bool:
    role = schema.get(SUBJECT_ROLE_KEY)
    if isinstance(role, str) and role.lower() in SUBJECT_ROLE_VALUES:
        return True
    return schema.get("in") == "path"


@dataclass(frozen=True)
class ToolDeclaration:
    """One tool, described once, by whoever knows what it returns.

    ``args`` maps argument name to label. ``subject`` names the argument carrying the
    entity the result is about and is deliberately not part of the sensitivity story: it is
    a different question with a different default, and conflating them is what the "trap in
    the default" below is about.
    """

    name: str
    args: Mapping[str, str] = field(default_factory=dict)
    subject: str | None = None

    @classmethod
    def from_schema(
        cls,
        name: str,
        parameters: Mapping[str, Any] | None,
        *,
        args: Mapping[str, str] | None = None,
    ) -> ToolDeclaration:
        """Read what the tool's own schema already says, and take the rest as given.

        The subject comes free for a customer who annotates their schema, which is the
        point: the declaration they already wrote for their own API documentation is the
        one Core reads.
        """
        return cls(
            name=name,
            args=dict(args or {}),
            subject=subject_arg_key(parameters),
        )


class DeclarationRegistry:
    """Every tool's declaration, and what a run withheld for want of one.

    **The trap in the default, said out loud.** Undeclared means most restrictive, and a
    silent restrictive default is a trap we have already sprung on this exact customer: a
    run wrote claims, no rule reported anything, and they read it as the product being
    broken. So this registry never withholds silently. Every run reports how many fields
    went undeclared, which tools they came from, and the configuration that releases them,
    which is the same discipline as the ``resolve_empty`` versus ``resolve_failed``
    taxonomy. A configuration state must never look like a broken product.

    **The default governs sensitivity only and explicitly not the subject key.** An
    undeclared subject falls through to Core's structural salience rung, which is today's
    behaviour and the thing CL36 improves on rather than replaces. Applying "most
    restrictive" there would withhold a fact whenever its subject argument was undeclared,
    which would defeat the CL36 fix shipping in the same change and be strictly worse than
    today.
    """

    def __init__(
        self,
        declarations: Iterable[ToolDeclaration] = (),
        *,
        is_undeclared_restricted: bool = True,
    ) -> None:
        self._by_name: dict[str, ToolDeclaration] = {
            declaration.name: declaration for declaration in declarations
        }
        self._is_undeclared_restricted = is_undeclared_restricted

    def register(self, declaration: ToolDeclaration) -> None:
        self._by_name[declaration.name] = declaration

    def register_tools(self, tools: Iterable[Any]) -> None:
        """Read declarations off a roster of tool specs that carry schemas."""
        for tool in tools:
            name = getattr(tool, "name", None)
            if not name or name in self._by_name:
                continue
            declaration = ToolDeclaration.from_schema(
                name, getattr(tool, "parameters", None)
            )
            if declaration.subject:
                self._by_name[name] = declaration

    def declaration_for(
        self, tool_name: str, args: Mapping[str, Any] | None = None
    ) -> tuple[dict[str, Any] | None, list[str]]:
        """The ``declared_sensitivity`` stamp for one step, and what it withheld.

        The second element is not diagnostics dressing. It is the mechanism by which a
        restrictive default stays legible: it names the tool, what was withheld, and the
        one thing the customer can do about it.
        """
        declaration = self._by_name.get(tool_name)
        stamp: dict[str, Any] = {}
        withheld: list[str] = []

        declared_args = dict(declaration.args) if declaration else {}
        if args and self._is_undeclared_restricted:
            undeclared = [key for key in args if key not in declared_args]
            for key in undeclared:
                declared_args[key] = UNDECLARED_SENSITIVITY
            if undeclared:
                withheld.append(
                    f"{tool_name}: {len(undeclared)} undeclared argument(s) "
                    f"({', '.join(sorted(undeclared))}) withheld as "
                    f"{UNDECLARED_SENSITIVITY}; declare the tool, or construct the "
                    "registry with is_undeclared_restricted=False, to release them"
                )
        if declared_args:
            stamp["args"] = declared_args
        # Bare string rather than a nested mapping, which is the shape the boundary has
        # accepted since #427 and the one Core's ``resolve_subject_arg_key`` reads. This
        # client's own type was the last thing stopping it being sent.
        if declaration and declaration.subject:
            stamp[SUBJECT_KEY] = declaration.subject
        return (stamp or None), withheld

    def is_fully_declared(self, tool_names: Iterable[str]) -> bool:
        """Whether every tool the run used carries a declaration.

        Gates cross-tenant org promotion: an undeclared or empty-declared foreign tool
        keeps the run's learnings agent-private. A run with no tool calls has nothing
        foreign to gate.
        """
        names = set(tool_names)
        if not names:
            return True
        return all(
            (declaration := self._by_name.get(name)) is not None and bool(declaration.args)
            for name in names
        )

    def output_label(self, tool_name: str) -> str | None:
        """The label a tool's own output carries, joined over what it declared.

        ``None`` for a tool that declared nothing, deliberately, and this is the decisive
        default in the other direction from the argument one. Treating an undeclared tool's
        output as most restrictive would taint every later argument that quoted it, which
        is taint explosion by another route: a label that is always the most restrictive
        one is the same as no label, and here it would mean withholding everything and
        telling the customer their corpus is empty.
        """
        declaration = self._by_name.get(tool_name)
        if declaration is None or not declaration.args:
            return None
        label: str | None = None
        for value in declaration.args.values():
            label = join(label, value)
        return label

    def record_outputs(
        self,
        prior_outputs: dict[str, str],
        tool_name: str,
        result: Any,
    ) -> None:
        """Add one step's output values to the run's join table, in place.

        Bounded in both directions: a value shorter than
        :data:`MIN_PROPAGATED_VALUE_LENGTH` is skipped because it matches by coincidence,
        and at most :data:`MAX_PROPAGATED_VALUES_PER_STEP` values are taken from one result
        because the check is against every later argument and the case this exists for is a
        field copied across, not a bulk transfer.

        A tool that declared nothing contributes nothing, so an undeclared tool cannot
        escalate anything through this route.
        """
        label = self.output_label(tool_name)
        if label is None:
            return
        taken = 0
        for value in _strings_in(result):
            if taken >= MAX_PROPAGATED_VALUES_PER_STEP:
                return
            if len(value) < MIN_PROPAGATED_VALUE_LENGTH:
                continue
            prior_outputs[value] = join(prior_outputs.get(value), label) or label
            taken += 1
        while len(prior_outputs) > MAX_PROPAGATED_VALUES_PER_RUN:
            prior_outputs.pop(next(iter(prior_outputs)))

    def propagate(
        self,
        tool_name: str,
        args: Mapping[str, Any],
        prior_outputs: Mapping[str, str],
    ) -> dict[str, str]:
        """The one-hop join: a value copied out of an earlier result keeps its label.

        ``prior_outputs`` maps a value seen in an earlier step's output to that step's
        label. A later argument that literally contains one of those values joins its
        label. One hop against this run's recorded outputs, never transitively, and it can
        only escalate.
        """
        escalated: dict[str, str] = {}
        if not prior_outputs:
            return escalated
        declaration = self._by_name.get(tool_name)
        declared = dict(declaration.args) if declaration else {}
        for key, value in args.items():
            if not isinstance(value, str) or not value:
                continue
            inherited: str | None = None
            for seen, label in prior_outputs.items():
                if seen and seen in value:
                    inherited = join(inherited, label)
            joined = join(declared.get(key), inherited)
            if joined is not None and joined != declared.get(key):
                escalated[key] = joined
        return escalated


# Bounded so a cyclic or pathologically nested tool result cannot turn the join table into
# a hang on the close path. Matches the receipt flattener's own bound for the same reason.
_MAX_RESULT_DEPTH = 8


def _strings_in(value: Any, depth: int = 0) -> Iterable[str]:
    """Every string inside a tool result, bounded in depth.

    Generous about shape rather than naming any tool's schema: a shape this cannot read
    contributes nothing, which costs an escalation and never a correctness claim.
    """
    if depth > _MAX_RESULT_DEPTH:
        return
    if isinstance(value, str):
        if value:
            yield value
        return
    if isinstance(value, Mapping):
        for item in value.values():
            yield from _strings_in(item, depth + 1)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings_in(item, depth + 1)
