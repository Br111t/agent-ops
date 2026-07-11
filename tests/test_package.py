"""Basic package smoke test."""

def test_agent_ops_package_imports() -> None:
    """Test that the agent_ops package can be imported."""
    import agent_ops

    assert agent_ops.__name__ == "agent_ops"