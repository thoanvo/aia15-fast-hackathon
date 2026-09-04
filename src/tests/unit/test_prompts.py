from langchain_app import prompts


def test_system_prompt_still_contains_preexisting_scope_rules():
    assert "You are the Database Query Assistant" in prompts.get_system_prompt(True)
    assert "search_knowledge_base(query=...)" in prompts.get_system_prompt(True)


def test_dynamic_only_tool_rule_scopes_answer_with_sql_and_has_no_fixed_tools():
    assert "You never write SQL and never access the database directly" in prompts._DYNAMIC_ONLY_TOOL_RULE
    assert "answer_with_sql" in prompts._DYNAMIC_ONLY_TOOL_RULE
    assert "No fixed business tools are registered" in prompts._DYNAMIC_ONLY_TOOL_RULE


def test_fixed_and_dynamic_tool_rule_still_forbids_writing_sql_and_scopes_answer_with_sql():
    """answer_with_sql takes the question, not SQL the model writes -
    the rule text should still say "never write SQL", now with an
    explicit callout that the exception doesn't apply even there."""
    assert "You never write SQL and never access the database directly" in prompts._FIXED_AND_DYNAMIC_TOOL_RULE
    assert "answer_with_sql" in prompts._FIXED_AND_DYNAMIC_TOOL_RULE
    assert "not even for" in prompts._FIXED_AND_DYNAMIC_TOOL_RULE


def test_fixed_and_dynamic_tool_rule_has_fixed_tool_decision_checklist():
    """The rule must spell out an explicit, numbered decision procedure -
    not just a one-line "use the right shape" instruction - so the model
    has a mechanical checklist rather than a single vague heuristic to
    generalize from (docs/13_fixed_tool_first_routing_plan.md)."""
    assert "Decide fixed tool vs. `answer_with_sql` with this checklist" in prompts._FIXED_AND_DYNAMIC_TOOL_RULE
    assert "ranking/aggregation dimension" in prompts._FIXED_AND_DYNAMIC_TOOL_RULE
    # Step 3: a fixed tool exists for the entity but no ranking dimension matches.
    assert "none of their ranking/aggregation dimensions match" in prompts._FIXED_AND_DYNAMIC_TOOL_RULE
    # Step 4: guards against substituting a wrong-dimension fixed tool instead of
    # correctly routing to a *different* fixed tool.
    assert "get_top_products_by_quantity" in prompts._FIXED_AND_DYNAMIC_TOOL_RULE


def test_fixed_tool_routing_suffix_has_no_schema_context_placeholder():
    """answer_with_sql takes the question, not a hand-written query, so
    the outer prompt needs no schema-context injection (schema discovery
    happens inside the tool's own graph) - no {schema_context} template
    variable should exist in either flag state."""
    for fixed_tools_enabled in (True, False):
        suffix = prompts._fixed_tool_routing_suffix(fixed_tools_enabled)
        assert "{schema_context}" not in suffix
        assert "answer_with_sql" in suffix


def test_fixed_tool_routing_suffix_covers_id_lookup_case():
    """An ID/name lookup on a dimension table has no fixed-tool argument
    to express it for any entity, so it must always route to
    answer_with_sql - the same class of gap oos_guard.py's reference
    corpus had for region ID/name lookups, fixed one layer up here."""
    for fixed_tools_enabled in (True, False):
        assert 'answer_with_sql(question="What region is region 1?")' in prompts._fixed_tool_routing_suffix(
            fixed_tools_enabled
        )


def test_fixed_tool_routing_suffix_covers_ranking_dimension_mismatch_case():
    """A fixed tool can exist for the entity while still not covering the
    question's ranking dimension - that must route to answer_with_sql too,
    not be forced into the entity's existing (wrong-dimension) fixed tool."""
    suffix = prompts._fixed_tool_routing_suffix(True)
    assert "Top regions by number of distinct customers" in suffix
    assert "get_region_performance" in suffix


def test_fixed_tool_routing_suffix_covers_exact_match_negative_example():
    """An open-ended-sounding request with an exact fixed-tool match must
    still call the fixed tool - guards against over-correcting toward
    answer_with_sql once more dynamic-SQL examples are added above it."""
    suffix = prompts._fixed_tool_routing_suffix(True)
    assert "get_top_products_by_profit(limit=10)" in suffix
    assert "NOT a case for `answer_with_sql`" in suffix


def test_broad_request_rule_dynamic_only_always_routes_to_answer_with_sql():
    assert "answer_with_sql" in prompts._BROAD_REQUEST_RULE_DYNAMIC_ONLY
    assert "No fixed business tools are registered" in prompts._BROAD_REQUEST_RULE_DYNAMIC_ONLY


def test_broad_request_rule_fixed_and_dynamic_prefers_plain_listing_over_ranked_tool():
    """A plain 'show all X' request (no ranking implied) should route to
    answer_with_sql, not be forced into a revenue-ranked fixed tool -
    but a request that DOES name a ranking should still use the fixed
    tool, so the rule must cover both directions."""
    assert "answer_with_sql" in prompts._BROAD_REQUEST_RULE_FIXED_AND_DYNAMIC
    assert "plain listing" in prompts._BROAD_REQUEST_RULE_FIXED_AND_DYNAMIC
    assert "use the matching fixed tool" in prompts._BROAD_REQUEST_RULE_FIXED_AND_DYNAMIC


def test_broad_request_example_dynamic_only_always_calls_answer_with_sql():
    assert "answer_with_sql(question=...)" in prompts._BROAD_REQUEST_EXAMPLE_DYNAMIC_ONLY
    assert "get_top_customers" not in prompts._BROAD_REQUEST_EXAMPLE_DYNAMIC_ONLY


def test_broad_request_example_fixed_and_dynamic_calls_answer_with_sql_for_plain_listing():
    assert 'answer_with_sql(question="Show me all customers information")' in prompts._BROAD_REQUEST_EXAMPLE_FIXED_AND_DYNAMIC
    # The contrasting ranked-request example must still point at the fixed tool.
    assert "get_top_customers" in prompts._BROAD_REQUEST_EXAMPLE_FIXED_AND_DYNAMIC


def test_system_prompt_reflects_fixed_tools_enabled_true():
    system_prompt = prompts.get_system_prompt(True)
    assert "answer_with_sql" in system_prompt
    assert prompts._tool_rule(True) == prompts._FIXED_AND_DYNAMIC_TOOL_RULE
    assert prompts._broad_request_rule(True) == prompts._BROAD_REQUEST_RULE_FIXED_AND_DYNAMIC
    assert prompts._broad_request_example(True) == prompts._BROAD_REQUEST_EXAMPLE_FIXED_AND_DYNAMIC
    assert "get_top_products" in system_prompt


def test_system_prompt_reflects_fixed_tools_enabled_false():
    system_prompt = prompts.get_system_prompt(False)
    assert "answer_with_sql" in system_prompt
    assert prompts._tool_rule(False) == prompts._DYNAMIC_ONLY_TOOL_RULE
    assert prompts._broad_request_rule(False) == prompts._BROAD_REQUEST_RULE_DYNAMIC_ONLY
    assert prompts._broad_request_example(False) == prompts._BROAD_REQUEST_EXAMPLE_DYNAMIC_ONLY
    assert prompts._DYNAMIC_ONLY_TOOL_RULE in system_prompt
    assert "get_top_products(limit=5)" not in system_prompt


def test_get_system_prompt_matches_real_environment_flag_state():
    """Whatever FIXED_TOOLS_ENABLED actually resolves to from the real .env
    in this environment (not mocked), get_system_prompt() called with that
    same value must reflect it. Deliberately doesn't assert a specific
    value: FIXED_TOOLS_ENABLED is meant to be environment-configurable, so
    a real .env change must not make this test start failing."""
    from config.settings import is_fixed_tools_enabled

    fixed_tools_enabled = is_fixed_tools_enabled()
    system_prompt = prompts.get_system_prompt(fixed_tools_enabled)
    assert "answer_with_sql" in system_prompt
    if fixed_tools_enabled:
        assert "get_top_products" in system_prompt
    else:
        assert prompts._DYNAMIC_ONLY_TOOL_RULE in system_prompt
        assert "get_top_products(limit=5)" not in system_prompt


def test_agent_prompt_has_no_schema_context_input_variable():
    """schema_context is no longer an input variable in either flag
    state - schema discovery is entirely internal to sql_graph.py now."""
    assert "schema_context" not in prompts.get_agent_prompt(True).input_variables
    assert "schema_context" not in prompts.get_agent_prompt(False).input_variables
