def topological_sort(deps: dict[str, set[str]]) -> list[str]:
    """
    Return nodes in topological order (dependencies before dependents).
    Assumes no cycles (validate_graph checks this).
    Uses Kahn's algorithm.
    """
    # Build reverse dependency map (who depends on whom)
    reverse_deps: dict[str, set[str]] = {node: set() for node in deps}
    for node, dependencies in deps.items():
        for dep in dependencies:
            if dep in reverse_deps:
                reverse_deps[dep].add(node)

    # Calculate in-degree (number of dependencies for each node)
    in_degree = {node: len(dependencies) for node, dependencies in deps.items()}

    # Start with nodes that have no dependencies
    queue = [node for node, degree in in_degree.items() if degree == 0]
    result = []

    while queue:
        node = queue.pop(0)
        result.append(node)
        for dependent in reverse_deps[node]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    return result
