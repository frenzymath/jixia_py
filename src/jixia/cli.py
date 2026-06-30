import logging
from pathlib import Path
from typing import Annotated

from . import run as run_module
from .run import LeanProject
from .structs import ALL_PLUGINS, LeanName, Plugin, parse_name

INSTALL_HINT = (
    "The jixia CLI requires the optional 'cli' extra. "
    "Install with: pip install 'jixia[cli]'"
)


def load_typer():
    try:
        import typer
    except ModuleNotFoundError as exc:
        raise SystemExit(INSTALL_HINT) from exc
    return typer


def parse_names(value: str | None) -> list[LeanName] | None:
    if value is None:
        return None
    names = [name.strip() for name in value.split(",")]
    return [parse_name(name) for name in names if name]


def parse_plugins(value: str) -> list[Plugin]:
    plugins = [plugin.strip() for plugin in value.split(",") if plugin.strip()]
    invalid = sorted(set(plugins) - set(ALL_PLUGINS))
    if invalid:
        valid = ", ".join(ALL_PLUGINS)
        raise ValueError(
            f"unknown plugin(s): {', '.join(invalid)}; expected one of: {valid}"
        )
    return plugins


typer = load_typer()
app = typer.Typer()


@app.command(no_args_is_help=True)
def run(
    project_root: Annotated[
        Path, typer.Argument(help="Lean project root containing the lakefile.")
    ],
    base_dir: Annotated[
        Path | None,
        typer.Option(
            help="Directory to scan for Lean files. Defaults to PROJECT_ROOT."
        ),
    ] = None,
    prefixes: Annotated[
        str | None,
        typer.Option(
            help="Comma-separated Lean module prefixes to process, e.g. Mathlib,Std,Init."
        ),
    ] = None,
    plugins: Annotated[
        str,
        typer.Option(help="Comma-separated plugins to run."),
    ] = ",".join(ALL_PLUGINS),
    output_dir: Annotated[
        Path,
        typer.Option(help="Output directory, relative to PROJECT_ROOT."),
    ] = Path(".jixia"),
    jixia_executable: Annotated[
        Path | None,
        typer.Option(help="Path to the jixia executable."),
    ] = None,
    max_workers: Annotated[
        int | None,
        typer.Option(help="Maximum number of worker threads."),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(help="Run jixia even when output files already exist."),
    ] = False,
    run_initializers: Annotated[
        bool,
        typer.Option(
            "--initializers/--no-initializers",
            help="Run Lean initializers during analysis.",
        ),
    ] = True,
    mathlib: Annotated[
        bool,
        typer.Option(
            "--mathlib/--no-mathlib",
            help="Add options that match mathlib's Lean configuration.",
        ),
    ] = True,
    log_level: Annotated[
        str,
        typer.Option(help="Python logging level."),
    ] = "INFO",
) -> None:
    logging.basicConfig(level=log_level.upper())
    try:
        selected_plugins = parse_plugins(plugins)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc

    if jixia_executable is not None:
        run_module.executable = jixia_executable

    project = LeanProject(project_root, output_dir=output_dir)
    project.batch_run_jixia(
        base_dir=base_dir,
        prefixes=parse_names(prefixes),
        plugins=selected_plugins,
        run_initializers=run_initializers,
        force=force,
        max_workers=max_workers,
        mathlib=mathlib,
    )


def main() -> None:
    app()
