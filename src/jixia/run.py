import concurrent.futures
import logging
import os
import subprocess
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path
from string import Template
from subprocess import CompletedProcess
from typing import Optional, Iterable, TypeVar

from .structs import AnyPath, LeanName, Plugin, pp_name, is_prefix_of, plugin_short_name, ALL_PLUGINS, ModuleInfo

logger = logging.getLogger(__name__)

executable: AnyPath = "jixia"
"""path to jixia executable"""


def run_jixia(
        file: AnyPath,
        module: Optional[str] = None,
        root: Optional[Path] = None,
        plugins: Iterable[Plugin] = ALL_PLUGINS,
        output_template: Template = Template("$file_dir/$module.$p.json"),
        run_initializers: bool = True,
        force: bool = False,
) -> Optional[CompletedProcess]:
    """
    Run jixia with given options.

    :param file: Lean source file to be analyzed
    :param module: module name, used in output_template.  defaults to the base name of file.
    :param root: project root, can be None if the file is stand-alone
    :param plugins: names of plugins to run
    :param output_template: a :class:`Template` object to calculate the output file name
        the following values are available to the template:

            - root: the project root
            - file_dir: parent directory of source file
            - module: module name
            - plugin: full name of the plugin
            - p: short name of the plugin
    :param run_initializers: run initializers in analysis.  set to True for mathlib
    :param force: always run jixia even if all output files are already present
    :return: the completed process object, or None if jixia was not run (when force is False and all output files are already present)
    """
    file = Path(file)
    if module is None:
        module = file.stem

    args = ["lake", "env", executable]
    if run_initializers:
        args.append("-i")

    run = force
    for plugin in plugins:
        args.append("--" + plugin)
        p = plugin_short_name(plugin)
        output_file = output_template.substitute(root=root, file_dir=file.parent, module=module, plugin=plugin, p=p)
        output_file = Path(output_file)
        if not output_file.exists():
            run = True
        args.append(output_file)
    if run:
        args.append(file)
        logger.debug(f"run: {args}")
        return subprocess.run(args, stderr=subprocess.PIPE, cwd=root, text=True)


M = TypeVar("M", bound="RootModel")


class LeanProject:
    def __init__(self, root: AnyPath, output_dir: AnyPath = ".jixia"):
        """
        :param root: project root, where ``lakefile.lean`` or ``lakefile.toml`` is found
        :param output_dir: path of the directory where the output files will be placed, relative to `root`
        """
        self.root = Path(root)
        self.output_dir = self.root / output_dir

    def path_of_module(self, module_name: LeanName, base_dir: Optional[AnyPath] = None) -> Path:
        """Return the source file of the module"""
        if base_dir is None:
            base_dir = self.root
        return Path(base_dir) / Path(*module_name).with_suffix(".lean")

    # TODO: align with the build system and take packages into consideration
    def find_modules(self, base_dir: Optional[AnyPath] = None, include_hidden_dirs: bool = True) -> list[LeanName]:
        """Return the list of all Lean modules"""
        if base_dir is None:
            base_dir = self.root
        modules = []
        for path, dirs, files in os.walk(base_dir):
            module_path = Path(path).relative_to(base_dir).parts
            modules += [module_path + (f[:-5],) for f in files if f.endswith(".lean")]
            if not include_hidden_dirs:
                dirs[:] = [d for d in dirs if not d.startswith(".")]
        return modules

    def batch_run_jixia(
            self,
            *,
            base_dir: Optional[AnyPath] = None,
            prefixes: Optional[list[LeanName]] = None,
            plugins: Iterable[Plugin] = ALL_PLUGINS,
            run_initializers: bool = True,
            force: bool = False,
    ) -> list[tuple[LeanName, CompletedProcess]]:
        """
        Run jixia on every file in the context of this project.

        :param prefixes: only process modules with one of the prefixes
        :param plugins:
        :param run_initializers:
        :param force:
            see documentation of :func:`run_jixia`
        :return: a list of all (module, CompletedProcess | None) pairs
        """
        modules = self.find_modules(base_dir)
        if prefixes is not None:
            modules = [m for m in modules if any(is_prefix_of(p, m) for p in prefixes)]
        self.output_dir.mkdir(exist_ok=True)
        output_dir_path = self.output_dir.resolve()
        ret = []
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = {executor.submit(
                run_jixia,
                self.path_of_module(m, base_dir),
                pp_name(m),
                self.root,
                plugins,
                Template(str(output_dir_path) + "/$module.$p.json"),
                run_initializers,
                force,
            ): m for m in modules}
            for f in concurrent.futures.as_completed(futures):
                m = futures[f]
                r: CompletedProcess | None = f.result()
                ret.append((m, r))
                if r is None:
                    logger.info(f"skip {m}")
                else:
                    if r.returncode:
                        logger.error(f"error while processing {m}: {r.stderr}")
                        ret.append((m, r))
                    else:
                        logger.info(f"processed {m}: {r.stderr}")
        return ret

    def load_module_info(self, module: LeanName) -> ModuleInfo:
        filename = f"{pp_name(module)}.mod.json"
        with (self.output_dir / filename).open() as fp:
            return ModuleInfo.model_validate_json(fp.read())

    def load_info(self, module: LeanName, cls: type[M]) -> list[M]:
        filename = f"{pp_name(module)}.{plugin_short_name(cls._plugin_name)}.json"
        return cls.from_json_file(self.output_dir / filename)
