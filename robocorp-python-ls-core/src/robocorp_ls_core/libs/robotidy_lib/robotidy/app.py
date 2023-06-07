import os
import sys
from difflib import unified_diff
from typing import Dict

try:
    import rich_click as click
except ImportError:  # Fails on vendored-in LSP plugin
    import click

from robot.api import get_model
from robot.errors import DataError

from robotidy import utils
from robotidy.config import MainConfig
from robotidy.disablers import RegisterDisablers
from robotidy.rich_console import console


class Robotidy:
    def __init__(self, main_config: "MainConfig"):
        self.main_config = main_config
        self.config = main_config.default_loaded

    def get_model(self, source):
        if utils.rf_supports_lang():
            return get_model(source, lang=self.config.language)
        return get_model(source)

    def transform_files(self):
        changed_files = 0
        for source, config in self.main_config.get_sources_with_configs():
            self.config = config
            disabler_finder = RegisterDisablers(self.config.formatting.start_line, self.config.formatting.end_line)
            try:
                stdin = False
                if str(source) == "-":
                    stdin = True
                    if self.config.verbose:
                        click.echo("Loading file from stdin")
                    source = self.load_from_stdin()
                elif self.config.verbose:
                    click.echo(f"Transforming {source} file")
                model = self.get_model(source)
                model_path = model.source
                disabler_finder.visit(model)
                if disabler_finder.file_disabled:
                    continue
                diff, old_model, new_model, model = self.transform_until_stable(model, disabler_finder)
                if diff:
                    changed_files += 1
                self.output_diff(model_path, old_model, new_model)
                if stdin:
                    self.print_to_stdout(new_model)
                elif diff:
                    self.save_model(model_path, model)
            except DataError:
                click.echo(
                    f"Failed to decode {source}. Default supported encoding by Robot Framework is UTF-8. Skipping file"
                )
                pass
        if not self.config.check or not changed_files:
            return 0
        return 1

    def transform_until_stable(self, model, disabler_finder):
        diff, old_model, new_model = self.transform(model, disabler_finder.disablers)
        reruns = self.config.reruns
        while diff and reruns:
            model = get_model(new_model.text)
            disabler_finder.visit(model)
            new_diff, _, new_model = self.transform(model, disabler_finder.disablers)
            if not new_diff:
                break
            reruns -= 1
        return diff, old_model, new_model, model

    def transform(self, model, disablers):
        old_model = utils.StatementLinesCollector(model)
        for transformer in self.config.transformers:
            setattr(transformer, "disablers", disablers)  # set dynamically to allow using external transformers
            transformer.visit(model)
        new_model = utils.StatementLinesCollector(model)
        return new_model != old_model, old_model, new_model

    @staticmethod
    def load_from_stdin() -> str:
        return sys.stdin.read()

    def print_to_stdout(self, collected_lines):
        if not self.config.show_diff:
            click.echo(collected_lines.text)

    def save_model(self, source, model):
        if self.config.overwrite:
            output = self.config.output or source
            utils.ModelWriter(output=output, newline=self.get_line_ending(source)).write(model)

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
        self, path: str, old_model: utils.StatementLinesCollector, new_model: utils.StatementLinesCollector
    ):
        if not self.config.show_diff:
            return
        old = [l + "\n" for l in old_model.text.splitlines()]
        new = [l + "\n" for l in new_model.text.splitlines()]
        lines = list(unified_diff(old, new, fromfile=f"{path}\tbefore", tofile=f"{path}\tafter"))
        if not lines:
            return
        if self.config.color:
            output = utils.decorate_diff_with_color(lines)
        else:
            output = utils.escape_rich_markup(lines)
        for line in output:
            console.print(line, end="", highlight=False, soft_wrap=True)
