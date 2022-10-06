import os
import sys
from difflib import unified_diff
from typing import Optional, Pattern, Tuple

try:
    import rich_click as click
except ImportError:  # Fails on vendored-in LSP plugin
    import click

    escape = None

from robot.api import get_model
from robot.errors import DataError

from robotidy.config import Config
from robotidy.disablers import RegisterDisablers
from robotidy.utils import ModelWriter, StatementLinesCollector, decorate_diff_with_color, escape_rich_markup

try:
    from robotidy.rich_console import console
except ImportError:  # Fails on vendored-in LSP plugin
    console = None


class Robotidy:
    def __init__(self, config: Config):
        self.config = config

    def transform_files(self):
        changed_files = 0
        disabler_finder = RegisterDisablers(self.config.formatting.start_line, self.config.formatting.end_line)
        for source in self.config.sources:
            try:
                stdin = False
                if str(source) == "-":
                    stdin = True
                    if self.config.verbose:
                        click.echo("Loading file from stdin")
                    source = self.load_from_stdin()
                elif self.config.verbose:
                    click.echo(f"Transforming {source} file")
                model = get_model(source)
                disabler_finder.visit(model)
                if disabler_finder.file_disabled:
                    continue
                diff, old_model, new_model = self.transform(model, disabler_finder.disablers)
                if diff:
                    changed_files += 1
                self.output_diff(model.source, old_model, new_model)
                if stdin:
                    self.print_to_stdout(new_model)
                elif diff:
                    self.save_model(model.source, model)
            except DataError:
                click.echo(
                    f"Failed to decode {source}. Default supported encoding by Robot Framework is UTF-8. Skipping file"
                )
                pass
        if not self.config.check or not changed_files:
            return 0
        return 1

    def transform(self, model, disablers):
        old_model = StatementLinesCollector(model)
        for transformer in self.config.transformers:
            setattr(transformer, "disablers", disablers)  # set dynamically to allow using external transformers
            transformer.visit(model)
        new_model = StatementLinesCollector(model)
        return new_model != old_model, old_model, new_model

    @staticmethod
    def load_from_stdin() -> str:
        return sys.stdin.read()

    def print_to_stdout(self, collected_lines):
        if not self.config.show_diff:
            click.echo(collected_lines.text)

    def save_model(self, source, model):
        if self.config.overwrite:
            output = self.config.output or model.source
            ModelWriter(output=output, newline=self.get_line_ending(source)).write(model)

    def get_line_ending(self, path: str):
        if self.config.formatting.line_sep == "auto":
            with open(path) as f:
                f.readline()
                if f.newlines is None:
                    return os.linesep
                if isinstance(f.newlines, str):
                    return f.newlines
                else:
                    return f.newlines[0]
        return self.config.formatting.line_sep

    def output_diff(
        self,
        path: str,
        old_model: StatementLinesCollector,
        new_model: StatementLinesCollector,
    ):
        if not self.config.show_diff:
            return
        old = [l + "\n" for l in old_model.text.splitlines()]
        new = [l + "\n" for l in new_model.text.splitlines()]
        lines = list(unified_diff(old, new, fromfile=f"{path}\tbefore", tofile=f"{path}\tafter"))
        if not lines:
            return
        if self.config.color:
            output = decorate_diff_with_color(lines)
        else:
            output = escape_rich_markup(lines)
        for line in output:
            console.print(line, end="", highlight=False, soft_wrap=True)
