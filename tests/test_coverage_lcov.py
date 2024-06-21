import os

from coverage_lcov import __version__, converter, cli


def test_version() -> None:
    assert __version__ == "0.3.0"


def test_parse_sample_coverage_file() -> None:
    this_dir = os.path.dirname(__file__)
    conv = converter.Converter(
        True,
        os.path.join(this_dir, ".coveragerc.sample"),
        os.path.join(this_dir, ".coverage.sample"),
    )
    assert conv.get_lcov()
    conv.print_lcov()
    conv.create_lcov(os.path.join(this_dir, "lcov.info"))


def test_cli() -> None:
    this_dir = os.path.dirname(__file__)
    cli.__main_internal__(
        os.path.join(this_dir, ".coverage.sample"),
        os.path.join(this_dir, "lcov.info"),
        os.path.join(this_dir, ".coveragerc.sample"),
        True,
        True,
    )
    cli.__main_internal__(
        os.path.join(this_dir, ".coverage.sample"),
        os.path.join(this_dir, "lcov.info"),
        os.path.join(this_dir, ".coveragerc.sample"),
        True,
        False,
    )
