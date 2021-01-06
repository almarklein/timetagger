def run_tests(scope):
    """Run all test functions in the given scope."""
    for func in list(scope.values()):
        if callable(func) and func.__name__.startswith("test_"):
            print(f"Running {func.__name__} ...")
            func()
    print("Done")
