def test_package_importable() -> None:
    import flexorch_mcp

    assert flexorch_mcp.__version__ == "0.1.1"
