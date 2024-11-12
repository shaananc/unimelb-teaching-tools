import json
import argparse
import glob
from pathlib import Path
from datetime import datetime, timezone
import re
import os
from uuid import uuid4 as uuid
import shutil
import subprocess
import difflib
import logging
from rich.logging import RichHandler

# requires Python 3.9+
# pip install jsondiff pyyaml

from jsondiff import diff
import yaml
from yaml.dumper import Dumper
from yaml.nodes import Node

# Set up logging
logger = logging.getLogger(__name__)
FORMAT = "%(message)s"
rich_handler = RichHandler(markup=True)
file_handler = logging.FileHandler(filename="unimelblib.log")
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s %(name)-12s %(levelname)-8s %(message)s", datefmt="%d-%b-%y %H:%M:%S"
))

logging.basicConfig(
    level="INFO",
    format=FORMAT,
    datefmt="[%X]",
    handlers=[rich_handler, file_handler],
)

import rich.traceback
rich.traceback.install()
# Utility functions for colored output
def fail(s):
    """Format a string with red color for failure."""
    return f"[bold red]{s}[/bold red]"

def ok(s):
    """Format a string with green color for success."""
    return f"[bold green]{s}[/bold green]"

def dbg(s):
    """Format a string with dark grey color for debugging."""
    return f"[dim]{s}[/dim]"

def rm_rf(pth):
    """Recursively remove a directory and its contents."""
    if not pth.is_dir():
        return
    for sub in pth.iterdir():
        if sub.is_dir():
            rm_rf(sub)
        else:
            sub.unlink()
    pth.rmdir()

def timestamp():
    """Get the current timestamp in ISO format with UTC timezone."""
    return datetime.now(timezone.utc).isoformat()

def is_multiline_string(string):
    """Check if a string contains any newline characters."""
    return any(c in string for c in "\u000a\u000d\u001c\u001d\u001e\u0085\u2028\u2029")

def str_presenter(dumper: Dumper, data: str) -> Node:
    """Present strings in YAML with appropriate formatting based on length and content."""
    if is_multiline_string(data):
        style = "|"
    elif len(data) > 50:
        style = ">"
    else:
        style = None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)

yaml.add_representer(str, str_presenter)

class Loader(yaml.SafeLoader):
    """Custom YAML loader that supports file inclusion."""
    def __init__(self, stream):
        self._root = os.path.split(stream.name)[0]
        super().__init__(stream)

    def include(self, node):
        filename = os.path.join(self._root, self.construct_scalar(node))
        with open(filename, "r") as f:
            return yaml.load(f, Loader)

Loader.add_constructor("!include", Loader.include)

KEYS_WITH_DUMPS_VALUES = (
    "workspace",
    "tests",
    "solutions",
    "options",
    "choices",
    "blockly_blocks",
)

def dump_one_workspace(workspace, wd):
    """Dump one workspace to the specified directory."""
    for entry in workspace:
        wd.mkdir(parents=True, exist_ok=True)
        path = wd / entry["path"]
        with open(path, "w") as f:
            f.write(entry["content"])

def load_one_workspace(wd, workspace=None):
    """Load one workspace from the specified directory."""
    if workspace is None:
        workspace = []
    old_workspace = {entry["path"]: entry for entry in workspace}
    workspace = []

    for path in glob.glob(f"{wd}/*"):
        path = Path(path)
        fname = path.name
        entry = old_workspace.get(
            fname,
            {
                "is_static": False,
                "metadata": "",
                "undeletable": True,
                "unrenamable": True,
                "uuid": str(uuid()),
                "path": fname,
            },
        )
        with open(path) as f:
            entry["content"] = f.read()
        workspace.append(entry)
    return workspace

FILETYPE_NAMES = {
    0: "stdio",
    1: "stdout",
    2: "stderr",
    3: "stdin",
    4: "Normal In",
    5: "Normal Out",
    6: "pyunit",
    10: "custom_driver",
    22: "multichoice",
}
FILETYPE_NOS = {v: k for k, v in FILETYPE_NAMES.items()}

def load_problem_json(json_path, as_file=True):
    """Load problem JSON from a file or a JSON object."""
    if as_file:
        with open(json_path) as f:
            obj = json.load(f)
    else:
        obj = json.loads(json.dumps(json_path))

    for k in KEYS_WITH_DUMPS_VALUES:
        if not obj[k]:
            continue
        try:
            obj[k] = json.loads(obj[k])
        except json.decoder.JSONDecodeError:
            import ipdb; ipdb.set_trace()
            import sys; sys.exit(1)
    return obj

class Problem:
    """Class to manage and manipulate problem data."""
    def __init__(self, ex, internal_json=None, output_dir="output/grok_exercises"):
        """Initialize the Problem instance with exercise name and optional internal JSON data."""
        self.internal_json = internal_json
        self.ex = ex
        self.wd: Path = Path(output_dir) / ex
        self.wd.mkdir(parents=True, exist_ok=True)
        self.load_json()
        self.ensure_directories()

    def ensure_directories(self):
        """Ensure required directories and files are present."""
        if not (self.wd / "solutions").is_dir():
            self.dump_solutions()
        if not (self.wd / "workspace").is_dir():
            self.dump_workspace()
        if not (self.wd / "content.md").exists():
            self.dump_content()
        if not (self.wd / "solution_notes.md").exists():
            self.dump_solution_notes()
        if not (self.wd / "problem.yaml").exists():
            self.dump_yaml()
        if not (self.wd / "tests").is_dir():
            self.dump_tests()

    def load(self):
        """Load JSON and dump to tests, content, yaml, etc."""
        logger.info("Loading JSON and dumping to tests, content, yaml, etc...")
        self.load_json()
        self.dump_tests()
        self.dump_content()
        self.dump_solution_notes()
        self.dump_solutions()
        self.dump_workspace()
        self.dump_yaml()
        logger.info("Done.")

    def dump(self, force=False):
        """Dump JSON and load data, optionally forcing the operation."""
        if force:
            self.load_all()
        if force or self.test():
            self.backup_json()
            logger.info("Dumping JSON...")
            self.dump_json()
            logger.info("Done.")
            self.load()
        else:
            logger.info("Tests failed, failed to dump")

    def load_all(self):
        """Load all components (YAML, content, solution notes, solutions, workspace, tests)."""
        self.load_yaml()
        self.load_content()
        self.load_solution_notes()
        self.load_solutions()
        self.load_workspace()
        self.load_tests()

    def test(self):
        """Run tests on the problem and return whether they all pass."""
        self.load_all()
        wd = self.wd / "tmp"
        rm_rf(wd)
        wd.mkdir()
        passed = True
        logger.info("-- Begin test suite")
        for solution in glob.glob(f"{self.wd}/solutions/*"):
            logger.info(f"Test solution: {solution}")
            self.setup_workspace(wd, solution)
            out = subprocess.run(
                ["make", "build"],
                cwd=wd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            logger.debug(dbg(out.stdout.decode("unicode_escape")))
            passed &= self.run_tests(wd, out)
        logger.info(ok("✓ all tests passed") if passed else fail("✗ some tests failed"))
        if not passed:
            import sys
            sys.exit(1)
            import ipdb
            ipdb.set_trace()
        return passed

    def setup_workspace(self, wd, solution):
        """Set up the workspace for testing by copying files."""
        for file in glob.glob(f"{self.wd}/workspace/*"):
            shutil.copy(file, wd)
        for file in glob.glob(f"{solution}/*"):
            shutil.copy(file, wd)

    def run_tests(self, wd, out):
        """Run tests on the workspace and return whether they all pass."""
        passed = True
        for test_no, test in enumerate(self.obj["tests"]["tests"]):
            test_wd = wd / "out" / str(test_no)
            test_wd.mkdir(parents=True, exist_ok=True)
            logger.info(f"Testing #{test_no}: {test['onpass']} ({test['label']}) ... ")
            content = {t["type"]: t["content"] for t in test["files"]}
            stdin = content.get(3, "")
            expected_stdout = content.get(1, content.get(0, None))
            expected_stderr = content.get(2, None)
            driver = content.get(10, None)
            pyunit_test = content.get(6, None)
            stdio = content.get(0, None)

            if driver:
                # Custom driver execution
                with open(wd / "driver.py", "w") as f:
                    f.write(driver)
                out = subprocess.run(
                    ["python", "driver.py"],
                    cwd=wd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                )
            elif pyunit_test:
                # PyUnit test execution
                pyunit_test_file = self.create_pyunit_test(wd, pyunit_test)
                out = subprocess.run(
                    ["python", "-m", "unittest", pyunit_test_file],
                    cwd=wd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                )
            elif stdio:
                # stdio tests
                user_inputs, expected_outputs = self.parse_stdio(stdio)
                out = subprocess.run(
                    ["python", "program.py"],
                    input="\n".join(user_inputs),
                    cwd=wd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                )
                expected_stdout = "\n".join(expected_outputs)
                import ipdb
                ipdb.set_trace()
                pass
            else:
                # Standard input/output tests
                with open(wd / "problem.py") as f:
                    script = f.read()
                with open(wd / "stdin.txt", "w") as f:
                    f.write(stdin)
                out = subprocess.run(
                    ["python", "problem.py"],
                    input=stdin if stdin else None,
                    cwd=wd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                )

            passed &= self.check_test_results(out, expected_stdout, expected_stderr)
            self.save_test_results(test_wd, out)
        return passed

    def parse_stdio(self, stdio):
        """Parse stdio format to separate user inputs and expected outputs."""
        lines = stdio.splitlines()
        user_inputs = []
        expected_outputs = []
        for line in lines:
            if "@@@" in line:
                prompt, user_input = line.split("@@@")
                expected_outputs.append(prompt.strip())
                user_inputs.append(user_input.strip())
            else:
                expected_outputs.append(line.strip())
        return user_inputs, expected_outputs

    def create_pyunit_test(self, wd, pyunit_test):
        """Create a PyUnit test file from the provided test content."""
        pyunit_lines = pyunit_test.splitlines()
        pyunit_test_file = wd / "test_pyunit.py"
        with open(pyunit_test_file, "w") as f:
            f.write("import unittest\n")
            f.write(f"from problem import {pyunit_lines[0]}\n")
            f.write(f"class TestProblem(unittest.TestCase):\n")
            f.write(f"    def test_case(self):\n")
            f.write(f"        self.assertEqual({pyunit_lines[0]}, {pyunit_lines[1]})\n")
            f.write("if __name__ == '__main__':\n")
            f.write("    unittest.main()\n")
        return pyunit_test_file

    def dump_tests(self):
        """Dump the tests to the specified directory."""
        wd = self.wd / "tests"
        rm_rf(wd)
        wd.mkdir()
        for test_no, entry in enumerate(self.obj["tests"]["tests"]):
            path = wd / str(test_no)
            path.mkdir()
            for file in entry["files"]:
                try:
                    if file["type"] == 6:
                        # PyUnit test
                        pyunit_test_file = self.create_pyunit_test(path, file["content"])
                    else:
                        # Other test types
                        with open(path / FILETYPE_NAMES[file["type"]], "w") as f:
                            f.write(file["content"])
                except KeyError:
                    import ipdb; ipdb.set_trace()
                    import sys; sys.exit(1)
            with open(path / "test.yaml", "w") as f:
                entry = {**entry}
                del entry["files"]
                yaml.dump(entry, f, width=60)

    def load_tests(self):
        """Load the tests from the specified directory."""
        wd = self.wd / "tests"
        self.obj["tests"]["tests"] = []
        for test_no, path in enumerate(sorted(glob.glob(f"{wd}/*"))):
            with open(path + "/test.yaml") as f:
                test = yaml.safe_load(f)
            test["files"] = []
            for fname in glob.glob(f"{path}/*"):
                if "yaml" in fname:
                    continue
                file = {}
                with open(fname) as f:
                    file["content"] = f.read()
                file["type"] = FILETYPE_NOS[Path(fname).name]
                test["files"].append(file)
            self.obj["tests"]["tests"].append(test)

    def check_test_results(self, out, expected_stout, expected_sterr):
        """Check the results of the tests against expected output."""
        passed_test = True
        if expected_stout is not None and out.stdout != expected_stout:
            logger.error(fail("✗ Failed! (stdout) ---"))
            logger.error(out.stdout)
            logger.error("--- Output ^ --- v Expected ---")
            logger.error(expected_stout)
            passed_test = False
        if expected_sterr is not None and out.stderr != expected_sterr:
            logger.error(fail("✗ Failed! (stderr) ---"))
            logger.error(out.stderr)
            logger.error("--- Output ^ --- v Expected ---")
            logger.error(expected_sterr)
            passed_test = False
        if passed_test:
            logger.info(ok("✓ Passed!"))
        return passed_test

    def save_test_results(self, test_wd, out):
        """Save the results of the tests to the specified directory."""
        with open(test_wd / "stdout", "w") as f:
            f.write(out.stdout)
        with open(test_wd / "stderr", "w") as f:
            f.write(out.stderr)




    def dump_workspace(self):
        """Dump the workspace to the specified directory."""
        dump_one_workspace(self.obj["workspace"], self.wd / "workspace")

    def load_workspace(self):
        """Load the workspace from the specified directory."""
        self.obj["workspace"] = load_one_workspace(self.wd / "workspace", self.obj["workspace"])

    def dump_solutions(self):
        """Dump the solutions to the specified directory."""
        for i, solution in enumerate(self.obj["solutions"]):
            dump_one_workspace(solution, self.wd / "solutions" / str(i))

    def load_solutions(self):
        """Load the solutions from the specified directory."""
        old_solutions = self.obj["solutions"]
        self.obj["solutions"] = []
        for i, path in enumerate(glob.glob(f"{self.wd}/solutions/*")):
            old_solution = None if i >= len(old_solutions) else old_solutions[i]
            self.obj["solutions"].append(load_one_workspace(path, old_solution))

    @property
    def json_path(self):
        """Get the path to the JSON file for the problem."""
        jpath = Path(f"output/grok_exercises/{self.ex}/*.json")
        logger.info(jpath.absolute())
        json_paths = glob.glob(str(jpath))
        assert len(json_paths) == 1
        path = Path(json_paths[0])
        self.slug = path.stem
        return path

    def diff_json(self):
        """Display the diff between the old and new JSON files."""
        old_json = load_problem_json(self.json_path)
        logger.info("diff:")
        logger.info(json.dumps(diff(old_json, self.obj, syntax="symmetric", marshal=True), indent=4, sort_keys=True))

    def diff_yaml(self):
        """Display the diff between the old and new YAML files."""
        yaml_txt = yaml.dump(self.obj, width=60).split("\n")
        old_json = load_problem_json(self.json_path)
        old_yaml_txt = yaml.dump(old_json, width=60).split("\n")
        logger.info(dbg("\n".join(difflib.unified_diff(old_yaml_txt, yaml_txt, n=0, lineterm=""))))

    def backup_json(self):
        """Backup the current JSON file."""
        old_json = load_problem_json(self.json_path)
        path = self.wd / "backups"
        path.mkdir(exist_ok=True)
        fname = path / f"{self.slug}-{old_json['updated_at']}.json"
        with open(fname, "w") as f:
            json.dump(old_json, f)
            logger.info(f"Backed up to {fname}")

    def load_json(self):
        """Load the JSON file for the problem."""
        if hasattr(self, "internal_json") and self.internal_json is not None:
            self.obj = load_problem_json(self.internal_json, as_file=False)
        else:
            self.obj = load_problem_json(self.json_path)

    def dump_json(self):
        """Dump the current state to the JSON file."""
        for k in KEYS_WITH_DUMPS_VALUES:
            self.obj[k] = json.dumps(self.obj[k])
        self.obj["updated_at"] = timestamp()
        with open(self.json_path, "w") as f:
            json.dump(self.obj, f)

    def dump_yaml(self):
        """Dump the current state to the YAML file."""
        with open(self.wd / "problem.yaml", "w") as f:
            yaml.dump(self.obj, f, width=60)

    def load_yaml(self):
        """Load the YAML file for the problem."""
        with open(self.wd / "problem.yaml") as f:
            self.obj = yaml.safe_load(f)

    def dump_content(self):
        """Dump the content to the markdown file."""
        with open(self.wd / "content.md", "w") as f:
            content = re.sub("^(#markdown)", f"# {self.obj['title']}", self.obj["content"])
            f.write(content)

    def load_content(self):
        """Load the content from the markdown file."""
        with open(self.wd / "content.md", "r") as f:
            content = f.read()
            self.obj["content"] = re.sub("^(# .*)", f"#markdown", content)

    def dump_solution_notes(self):
        """Dump the solution notes to the markdown file."""
        with open(self.wd / "solution_notes.md", "w") as f:
            solution = re.sub("^(#markdown)", f"# {self.obj['title']} - Solution Notes", self.obj["notes"])
            f.write(solution)

    def load_solution_notes(self):
        """Load the solution notes from the markdown file."""
        with open(self.wd / "solution_notes.md", "r") as f:
            solution = f.read()
            self.obj["notes"] = re.sub("^(# .*)", f"#markdown", solution)

def main():
    """Main function to parse arguments and process problems."""
    args = parse_args()
    if len(args.names) == 0:
        logger.info("Using all problems in directory")
        problems = [Path(p) for p in os.listdir("output/grok_exercises")]
        logger.info(problems)
    else:
        problems = args.names
    for problem_name in problems:
        logger.info(f"{problem_name} ------")
        problem = Problem(problem_name, output_dir=args.output_dir)
        if args.d:
            logger.info(f"Diffing problem {problem_name}")
            problem.load_all()
        elif args.w:
            logger.info(fail(f"Dumping problem {problem_name} if testing succeeds"))
            problem.dump()
        elif args.f:
            logger.info(fail(f"Dumping problem {problem_name}"))
            problem.dump(force=True)
        elif args.r:
            logger.info(f"Loading problem {problem_name}")
            problem.load()
            problem.test()
        else:
            problem.test()

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Parse and test Grok problems\nExpects to be placed within problems directory")
    parser.add_argument("names", help="exercise names, eg: ex1.02", nargs="*", default=None)
    parser.add_argument("-r", action="store_true", help="read json and overwrite local files")
    parser.add_argument("-w", action="store_true", help="write json (and backup current json), if testing succeeds")
    parser.add_argument("-f", action="store_true", help="force write json (and backup current json), ignoring testing")
    parser.add_argument("-d", action="store_true", help="diff only (json vs current work directory)")
    parser.add_argument("-o", "--output-dir", help="output directory", default="output/grok_exercises")
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    main()
