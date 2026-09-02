"""What the declaration registry must refuse, default to, and say out loud."""

from __future__ import annotations

from hyperstruck.runtime.declarations import (
    MAX_PROPAGATED_VALUES_PER_STEP,
    SECRET,
    SHAREABLE,
    UNDECLARED_SENSITIVITY,
    USER_DATA,
    DeclarationRegistry,
    ToolDeclaration,
    join,
    subject_arg_key,
)


def test_a_scan_may_escalate_a_label_and_may_never_lower_one() -> None:
    """A tool declared permissively whose output carries personal data is the case.

    The reverse is not: a tool declared restrictively whose content looks innocuous is not
    evidence that the declaration was wrong, so the join only ever goes one way.
    """
    assert join(SHAREABLE, SECRET) == SECRET
    assert join(SECRET, SHAREABLE) == SECRET
    assert join(None, USER_DATA) == USER_DATA
    assert join(USER_DATA, None) == USER_DATA


def test_an_ambiguous_subject_declaration_is_treated_as_no_declaration() -> None:
    """A clean single declaration is authoritative; anything else falls to salience.

    Picking one of two declared subjects would be a guess presented as the top rung of the
    entity ladder, which outranks the structural resolution that would otherwise have been
    right.
    """
    two = {
        "properties": {
            "company": {"type": "string", "role": "entity"},
            "vendor": {"type": "string", "role": "subject"},
        }
    }
    assert subject_arg_key(two) is None


def test_the_subject_is_read_from_the_schema_the_customer_already_wrote() -> None:
    schema = {
        "properties": {
            "company": {"type": "string", "role": "entity"},
            "limit": {"type": "integer"},
        }
    }
    assert subject_arg_key(schema) == "company"
    assert subject_arg_key({"properties": {"id": {"in": "path"}}}) == "id"
    assert subject_arg_key(None) is None


def test_the_subject_travels_as_a_bare_string_which_is_what_core_reads() -> None:
    """The shape the boundary has accepted since #427, and CL36's whole remaining half."""
    registry = DeclarationRegistry(
        [ToolDeclaration(name="lookup", args={"token": SECRET}, subject="company")]
    )
    stamp, _ = registry.declaration_for("lookup", {"token": "abc", "company": "Northwind Clinics"})
    assert stamp is not None
    assert stamp["subject"] == "company"
    assert isinstance(stamp["subject"], str)


def test_an_undeclared_argument_is_withheld_and_the_run_is_told_how_to_release_it() -> None:
    """A silent restrictive default is a trap already sprung on this exact customer.

    They ran a job that wrote claims, saw nothing reported, and read it as the product
    being broken. So the default restricts and the run says which tool, how many fields,
    and the one configuration change that releases them.
    """
    registry = DeclarationRegistry()
    stamp, withheld = registry.declaration_for("search", {"query": "q", "region": "eu"})
    assert stamp is not None
    assert stamp["args"] == {"query": UNDECLARED_SENSITIVITY, "region": UNDECLARED_SENSITIVITY}
    assert len(withheld) == 1
    assert "search" in withheld[0]
    assert "query, region" in withheld[0]
    assert "is_undeclared_restricted=False" in withheld[0]


def test_the_restrictive_default_governs_sensitivity_and_not_the_subject() -> None:
    """Applying "most restrictive" to the subject would defeat the CL36 fix.

    An undeclared subject falls through to Core's structural salience rung, which is
    today's behaviour. Withholding a fact whenever its subject argument went undeclared
    would be strictly worse than today rather than a safer version of it.
    """
    registry = DeclarationRegistry()
    stamp, _ = registry.declaration_for("search", {"query": "q"})
    assert stamp is not None
    assert "subject" not in stamp


def test_turning_the_default_off_declares_nothing_rather_than_declaring_shareable() -> None:
    """Not restricting is not the same as vouching for the value."""
    registry = DeclarationRegistry(is_undeclared_restricted=False)
    stamp, withheld = registry.declaration_for("search", {"query": "q"})
    assert stamp is None
    assert withheld == []


def test_org_promotion_is_gated_on_every_used_tool_carrying_a_declaration() -> None:
    registry = DeclarationRegistry([ToolDeclaration(name="a", args={"x": SECRET})])
    assert registry.is_fully_declared(["a"]) is True
    assert registry.is_fully_declared(["a", "b"]) is False
    # A run with no tool calls has nothing foreign to gate.
    assert registry.is_fully_declared([]) is True


def test_an_empty_declaration_does_not_count_as_a_declaration() -> None:
    """Registering a tool and saying nothing about it is silence, not a vouch."""
    registry = DeclarationRegistry([ToolDeclaration(name="a")])
    assert registry.is_fully_declared(["a"]) is False


def test_propagation_is_one_hop_and_can_only_escalate() -> None:
    """The common real case: an agent copies a field out of one result into the next call.

    Bounded to one hop against this run's own recorded outputs, because indiscriminate
    propagation ends with everything tainted and the label meaning nothing.
    """
    registry = DeclarationRegistry(
        [ToolDeclaration(name="send", args={"body": SHAREABLE})]
    )
    escalated = registry.propagate(
        "send",
        {"body": "the token is sk-live-123 now", "count": 4},
        {"sk-live-123": SECRET},
    )
    assert escalated == {"body": SECRET}


def test_propagation_leaves_an_already_stricter_declaration_alone() -> None:
    registry = DeclarationRegistry([ToolDeclaration(name="send", args={"body": SECRET})])
    assert registry.propagate("send", {"body": "x@y.com"}, {"x@y.com": USER_DATA}) == {}


def test_propagation_with_nothing_recorded_yet_changes_nothing() -> None:
    registry = DeclarationRegistry()
    assert registry.propagate("send", {"body": "anything"}, {}) == {}


def test_the_output_label_is_joined_over_what_the_tool_declared() -> None:
    registry = DeclarationRegistry(
        [
            ToolDeclaration(name="mixed", args={"a": SHAREABLE, "b": USER_DATA}),
            ToolDeclaration(name="bare", args={}),
        ]
    )
    assert registry.output_label("mixed") == USER_DATA
    # A tool that declared nothing contributes nothing, deliberately: treating its output
    # as most restrictive would taint every later argument that quoted it, which is taint
    # explosion by another route.
    assert registry.output_label("bare") is None
    assert registry.output_label("unknown") is None


def test_an_undeclared_tool_s_output_cannot_escalate_anything() -> None:
    registry = DeclarationRegistry()
    prior: dict[str, str] = {}
    registry.record_outputs(prior, "unknown", "ada@example.com")
    assert prior == {}


def test_a_declared_tool_s_output_values_enter_the_join_table() -> None:
    registry = DeclarationRegistry(
        [ToolDeclaration(name="lookup", args={"q": USER_DATA})]
    )
    prior: dict[str, str] = {}
    registry.record_outputs(
        prior, "lookup", {"rows": [{"email": "ada@example.com"}, {"note": "hi"}]}
    )
    # "hi" is below the length floor: a short value matches by coincidence, and every
    # coincidence is an escalation that withholds something the customer wanted.
    assert prior == {"ada@example.com": USER_DATA}


def test_the_join_table_is_bounded_so_a_bulk_result_cannot_hang_the_close() -> None:
    registry = DeclarationRegistry(
        [ToolDeclaration(name="dump", args={"q": USER_DATA})]
    )
    prior: dict[str, str] = {}
    registry.record_outputs(prior, "dump", [f"value-{index:05d}" for index in range(500)])
    assert len(prior) == MAX_PROPAGATED_VALUES_PER_STEP


def test_a_cyclic_result_is_bounded_rather_than_walked_forever() -> None:
    registry = DeclarationRegistry(
        [ToolDeclaration(name="looped", args={"q": USER_DATA})]
    )
    cyclic: dict[str, object] = {"value": "ada@example.com"}
    cyclic["self"] = cyclic
    prior: dict[str, str] = {}
    registry.record_outputs(prior, "looped", cyclic)
    assert "ada@example.com" in prior
