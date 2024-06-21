import logging
import sys
from typing import Any, List, Optional, Tuple, Union

import coverage
from coverage.misc import CoverageException, NoSource, NotPython
from coverage.python import PythonFileReporter, FileReporter
from coverage.results import Analysis

if sys.version_info < (3, 8):  # pragma: no cover
    from coverage.files import (
        FnmatchMatcher,
        prep_patterns,
    )
else:  # pragma: no cover
    from coverage.files import GlobMatcher, prep_patterns
    from coverage.types import TMorf

log = logging.getLogger("coverage_lcov.converter")

if sys.version_info < (3, 8):
    FileReportersList = List[Union[PythonFileReporter, Any]]
else:
    FileReportersList = List[Tuple[FileReporter, TMorf]]


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

    def get_file_reporters(self) -> FileReportersList:
        file_reporters: FileReportersList = self.cov_obj._get_file_reporters(  # pylint: disable=protected-access
            None
        )
        config = self.cov_obj.config

        if config.report_include:
            if sys.version_info < (3, 8):
                matcher = FnmatchMatcher(
                    prep_patterns(config.report_include), "report_include"
                )
                file_reporters = [
                    fr for fr in file_reporters if matcher.match(fr.filename)
                ]
            else:
                matcher = GlobMatcher(
                    prep_patterns(config.report_include),
                )
                file_reporters = [
                    (fr, morf)
                    for fr, morf in file_reporters
                    if matcher.match(fr.filename)
                ]

        if config.report_omit:
            if sys.version_info < (3, 8):
                matcher = FnmatchMatcher(
                    prep_patterns(config.report_omit), "report_omit"
                )
                file_reporters = [
                    fr for fr in file_reporters if not matcher.match(fr.filename)
                ]
            else:
                matcher = GlobMatcher(
                    prep_patterns(config.report_omit),
                )
                file_reporters = [
                    (fr, morf)
                    for fr, morf in file_reporters
                    if not matcher.match(fr.filename)
                ]

        if not file_reporters:  # pragma: no-cover
            raise CoverageException("No data to report.")

        return file_reporters

    def get_lcov(self) -> str:  # pylint: disable=too-many-branches
        """Get LCOV output

        This is shamelessly adapted from https://github.com/nedbat/coveragepy/blob/master/coverage/report.py

        """
        output = ""

        file_reporters = self.get_file_reporters()

        config = self.cov_obj.config

        for file_reporter_item in sorted(file_reporters):
            if sys.version_info < (3, 8):
                file_reporter = file_reporter_item
            else:
                file_reporter, morf = file_reporter_item
            try:
                if sys.version_info < (3, 8):
                    analysis = (
                        self.cov_obj._analyze(  # pylint: disable=protected-access
                            file_reporter
                        )
                    )
                    token_lines = analysis.file_reporter.source_token_lines()
                else:
                    analysis = self.cov_obj._analyze(  # pylint: disable=protected-access
                        morf
                    )
                    token_lines = file_reporter.source_token_lines()
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
                if sys.version_info < (3, 8):
                    if file_reporter.should_be_python():
                        if config.ignore_errors:
                            msg = "Couldn't parse Python file '{}'".format(  # pylint: disable=useless-suppression, bad-option-value, consider-using-f-string
                                file_reporter.filename
                            )
                            self.cov_obj._warn(  # pylint: disable=protected-access
                                msg, slug="couldnt-parse"
                            )
                    else:
                        raise
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
