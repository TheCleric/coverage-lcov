import logging
from typing import Any, List, Optional, Union

import coverage
from coverage.files import prep_patterns
try:
    from coverage.files import GlobMatcher
except ImportError:  # compatibility with coverage<7.0
    from coverage.files import FnmatchMatcher as GlobMatcher
from coverage.misc import CoverageException, NoSource, NotPython
from coverage.python import PythonFileReporter
from coverage.results import Analysis

log = logging.getLogger("coverage_lcov.converter")


def GlobMatcher_compat(pattern, name):
    """Cross-version compatibility function.

    Makes coverage_lcov compatible with older coverage versions
    """
    try:
        return GlobMatcher(  # pylint: disable=too-many-function-args
            pattern, name
        )
    except TypeError:
        return GlobMatcher(pattern)  # pylint: disable=too-many-function-args


class Converter:
    def __init__(
        self,
        relative_path: bool,
        config_file: Union[str, bool],
        data_file_path: str,
    ):
        self.relative_path = relative_path

        self.cov_obj = coverage.coverage(
            data_file=data_file_path, config_file=config_file
        )
        self.cov_obj.load()
        self.cov_obj.get_data()

    def get_file_reporters(self) -> List[Union[PythonFileReporter, Any]]:
        file_reporters: List[
            Union[PythonFileReporter, Any]
        ] = self.cov_obj._get_file_reporters(  # pylint: disable=protected-access
            None
        )
        config = self.cov_obj.config

        if config.report_include:
            matcher = GlobMatcher_compat(
                prep_patterns(config.report_include), "report_include"
            )
            file_reporters = [fr for fr in file_reporters if matcher.match(fr.filename)]

        if config.report_omit:
            matcher = GlobMatcher_compat(  # pylint: disable=too-many-function-args
                prep_patterns(config.report_omit), "report_omit"
            )
            file_reporters = [
                fr for fr in file_reporters if not matcher.match(fr.filename)
            ]

        if not file_reporters:
            raise CoverageException("No data to report.")

        return file_reporters

    def get_lcov(self) -> str:
        """Get LCOV output

        This is shamelessly adapted from https://github.com/nedbat/coveragepy/blob/master/coverage/report.py

        """
        output = ""

        file_reporters = self.get_file_reporters()

        config = self.cov_obj.config

        for file_reporter in sorted(file_reporters):
            try:
                analysis = self.cov_obj._analyze(  # pylint: disable=protected-access
                    file_reporter
                )
                token_lines = analysis.file_reporter.source_token_lines()
                if self.relative_path:
                    filename = file_reporter.relative_filename()
                else:
                    filename = file_reporter.filename
                output += "TN:\n"
                output += f"SF:{filename}\n"

                lines_hit = 0
                for i, _ in enumerate(token_lines, 1):
                    hits = get_hits(i, analysis)
                    if hits is not None:
                        if hits > 0:
                            lines_hit += 1
                        output += f"DA:{i},{hits}\n"

                output += f"LF:{len(analysis.statements)}\n"
                output += f"LH:{lines_hit}\n"
                output += "end_of_record\n"

            except NoSource:
                if not config.ignore_errors:
                    raise

            except NotPython:
                if file_reporter.should_be_python():
                    if config.ignore_errors:
                        msg = "Couldn't parse Python file '{}'".format(
                            file_reporter.filename
                        )
                        self.cov_obj._warn(  # pylint: disable=protected-access
                            msg, slug="couldnt-parse"
                        )

                    else:
                        raise

        return output

    def print_lcov(self) -> None:
        """Print LCOV output

        Print out the LCOV output

        """
        lcov_str = self.get_lcov()
        print(lcov_str)

    def create_lcov(self, output_file_path: str) -> None:
        lcov_str = self.get_lcov()

        with open(output_file_path, "w", encoding="ascii") as output_file:
            output_file.write(lcov_str)


def get_hits(line_num: int, analysis: Analysis) -> Optional[int]:
    if line_num in analysis.missing:
        return 0

    if line_num not in analysis.statements:
        return None

    return 1
