from murmur.executor import topological_sort


def test_topological_sort_simple_chain():
    """topological_sort should order nodes by dependencies."""
    deps = {
        "c": {"b"},
        "b": {"a"},
        "a": set(),
    }
    order = topological_sort(deps)
    assert order.index("a") < order.index("b")
    assert order.index("b") < order.index("c")


def test_topological_sort_parallel_nodes():
    """topological_sort should handle independent nodes."""
    deps = {
        "merge": {"a", "b"},
        "a": set(),
        "b": set(),
    }
    order = topological_sort(deps)
    assert order.index("a") < order.index("merge")
    assert order.index("b") < order.index("merge")
