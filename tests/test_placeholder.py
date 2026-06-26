def test_package_importable() -> None:
    import flexorch_mcp
    from importlib.metadata import version

    assert flexorch_mcp.__version__ == version("flexorch-mcp")
