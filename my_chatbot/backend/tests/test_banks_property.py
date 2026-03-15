"""Property-based tests for argument bank lookup correctness.

# Feature: debate-engine-integration, Property 4: Argument bank lookup correctness

**Validates: Requirements 3.5, 3.6, 3.7**
"""

from hypothesis import given, strategies as st, settings
from src.debate.argument_bank import ARGUMENT_BANK, get_claims, get_rebuttals

# Valid domains defined in the type system
VALID_DOMAINS = ["art", "science", "government", "human"]

# Build a mapping of valid objection keys per domain from the actual data
VALID_OBJECTIONS_PER_DOMAIN: dict[str, list[str]] = {}
for _domain in VALID_DOMAINS:
    rebuttals = ARGUMENT_BANK[_domain]["rebuttals"]
    assert isinstance(rebuttals, dict)
    VALID_OBJECTIONS_PER_DOMAIN[_domain] = list(rebuttals.keys())

# Strategy: pick a valid domain
domain_strategy = st.sampled_from(VALID_DOMAINS)

# Strategy: pick a domain and one of its existing objection keys
domain_and_existing_objection = domain_strategy.flatmap(
    lambda d: st.tuples(
        st.just(d),
        st.sampled_from(VALID_OBJECTIONS_PER_DOMAIN[d]),
    )
)

# Strategy: generate objection keys that do NOT exist in a given domain's rebuttals
domain_and_missing_objection = domain_strategy.flatmap(
    lambda d: st.tuples(
        st.just(d),
        st.text(min_size=1, max_size=30).filter(
            lambda key, dom=d: key not in VALID_OBJECTIONS_PER_DOMAIN[dom]
        ),
    )
)


class TestArgumentBankLookupCorrectness:
    """Property 4: Argument bank lookup correctness.

    For any valid domain, the argument bank shall return a non-empty claims
    list and a rebuttals dictionary. For any valid domain and objection key
    that exists in that domain's rebuttals, the returned rebuttals list shall
    be non-empty. For any valid domain and objection key that does not exist
    in that domain's rebuttals, the returned rebuttals list shall be empty.
    """

    @given(domain=domain_strategy)
    @settings(max_examples=100)
    def test_valid_domain_returns_non_empty_claims(self, domain: str) -> None:
        """For any valid domain, get_claims returns a non-empty list."""
        claims = get_claims(domain)
        assert isinstance(claims, list)
        assert len(claims) > 0, f"Claims for domain '{domain}' should be non-empty"
        assert all(isinstance(c, str) for c in claims)

    @given(domain=domain_strategy)
    @settings(max_examples=100)
    def test_valid_domain_has_rebuttals_dict(self, domain: str) -> None:
        """For any valid domain, the argument bank contains a rebuttals dictionary."""
        entry = ARGUMENT_BANK[domain]
        rebuttals = entry["rebuttals"]
        assert isinstance(rebuttals, dict), (
            f"Rebuttals for domain '{domain}' should be a dict"
        )

    @given(data=domain_and_existing_objection)
    @settings(max_examples=100)
    def test_existing_objection_returns_non_empty_rebuttals(
        self, data: tuple[str, str]
    ) -> None:
        """For any valid domain and existing objection key, get_rebuttals returns non-empty."""
        domain, objection = data
        rebuttals = get_rebuttals(domain, objection)
        assert isinstance(rebuttals, list)
        assert len(rebuttals) > 0, (
            f"Rebuttals for domain='{domain}', objection='{objection}' should be non-empty"
        )
        assert all(isinstance(r, str) for r in rebuttals)

    @given(data=domain_and_missing_objection)
    @settings(max_examples=100)
    def test_missing_objection_returns_empty_rebuttals(
        self, data: tuple[str, str]
    ) -> None:
        """For any valid domain and non-existing objection key, get_rebuttals returns empty."""
        domain, objection = data
        rebuttals = get_rebuttals(domain, objection)
        assert isinstance(rebuttals, list)
        assert len(rebuttals) == 0, (
            f"Rebuttals for domain='{domain}', missing objection='{objection}' should be empty"
        )
