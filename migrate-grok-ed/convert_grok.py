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

# requires Python 3.9+
# pip install jsondiff pyyaml

from jsondiff import diff
import yaml
from yaml.dumper import Dumper
from yaml.nodes import Node


def fail(s):
    """red string"""
    return "\u001b[31m" + s + "\u001b[0m"


def ok(s):
    """green string"""
    return "\u001b[32m" + s + "\u001b[0m"


def dbg(s):
    """gray string"""
    return "\u001b[30;1m" + s + "\u001b[0m"


def rm_rf(pth):
    """Delete non-empty directory https://stackoverflow.com/questions/303200/how-do-i-remove-delete-a-folder-that-is-not-empty"""
    if not pth.is_dir():
        return
    for sub in pth.iterdir():
        if sub.is_dir():
            rm_rf(sub)
        else:
            sub.unlink()
    pth.rmdir()  # if you just want to delete the dir content but not the dir itself, remove this line


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def is_multiline_string(string):
    return any(c in string for c in "\u000a\u000d\u001c\u001d\u001e\u0085\u2028\u2029")


def str_presenter(dumper: Dumper, data: str) -> Node:
    # https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data
    if is_multiline_string(data):  # check for multiline string
        style = "|"
    elif len(data) > 50:
        style = ">"
    else:
        style = None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


# yaml.representer.BaseRepresenter.represent_scalar = my_represent_scalar
yaml.add_representer(str, str_presenter)


class Loader(yaml.SafeLoader):
    # https://stackoverflow.com/questions/528281/how-can-i-include-a-yaml-file-inside-another

    def __init__(self, stream):

        self._root = os.path.split(stream.name)[0]

        super(Loader, self).__init__(stream)

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
    for entry in workspace:
        wd.mkdir(parents=True, exist_ok=True)
        path = wd / entry["path"]
        with open(path, "w") as f:
            f.write(entry["content"])


def load_one_workspace(wd, workspace=None):
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


# I don't know the difference between stdio and stdout.
FILETYPE_NAMES = {
    0: "stdio",
    1: "stdout",
    2: "stderr",
    3: "stdin",
    4: "Normal In",
    5: "Normal Out",
    22: "multichoice",
}
FILETYPE_NOS = {v: k for k, v in FILETYPE_NAMES.items()}

C_DRIVER = 20
PY_DRIVER = 0


def load_problem_json(json_path, as_file=True):
    if as_file:
        with open(json_path) as f:
            obj = json.load(f)
    else:
        obj = json.loads(json.dumps(json_path))
    # return json.load(f, object_hook=lambda d: SimpleNamespace(**d))

    # string -> obj for each of these attributes on the JSON object
    for k in KEYS_WITH_DUMPS_VALUES:
        if not obj[k]:
            continue
        try:
            obj[k] = json.loads(obj[k])
        except json.decoder.JSONDecodeError:
            import ipdb

            ipdb.set_trace()
            import sys

            sys.exit(1)
    return obj


class Problem:
    def __init__(self, ex, internal_json=None, output_dir=None):
        if internal_json:
            self.internal_json = internal_json
        self.ex = ex
        if output_dir is None:
            output_dir = Path(ex)  # Path(ex.replace('.', '-'))
        self.wd: Path = output_dir
        self.wd.mkdir(parents=True, exist_ok=True)
        self.load_json()
        if not (output_dir / "solutions").is_dir():
            self.dump_solutions()
        if not (output_dir / "workspace").is_dir():
            self.dump_workspace()
        if not (output_dir / "content.md").exists():
            self.dump_content()
        if not (output_dir / "solution_notes.md").exists():
            self.dump_solution_notes()
        if not (output_dir / "problem.yaml").exists():
            self.dump_yaml()
        if not (output_dir / "tests").is_dir():
            self.dump_tests()

    def load(self):
        """Load JSON, dumps to solutions, content, yaml, workspaces, etc."""
        print("Loading JSON and dumping to tests, content, yaml, etc...")
        self.load_json()

        self.dump_tests()
        self.dump_content()
        self.dump_solution_notes()
        self.dump_solutions()
        self.dump_workspace()
        self.dump_yaml()
        print("Done.")

    def dump(self, force=False):
        """Dumps JSON, loading from solutions, content, yaml, workspaces, etc."""
        if force:
            self.load_all()
        if force or self.test():
            self.backup_json()

            print("Dumping JSON...")
            self.dump_json()
            print("Done.")

            self.load()
        else:
            print("Tests failed, failed to dump")

    def load_all(self):
        self.load_yaml()
        self.load_content()
        self.load_solution_notes()
        self.load_solutions()
        self.load_workspace()
        self.load_tests()

    def test(self):
        self.load_all()

        wd = self.wd / "tmp"
        rm_rf(wd)
        wd.mkdir()  # fresh directory

        passed = True
        print("-- Begin test suite")
        for solution in glob.glob(f"{self.wd}/solutions/*"):
            print("Test solution: ", solution)
            # setup solution test workspace
            for file in glob.glob(f"{self.wd}/workspace/*"):
                shutil.copy(file, wd)
            for file in glob.glob(f"{solution}/*"):
                shutil.copy(file, wd)

            out = subprocess.run(
                ["make", "build"],
                cwd=wd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            print(dbg(out.stdout.decode("unicode_escape")))
            for test_no, test in enumerate(self.obj["tests"]["tests"]):
                test_wd = wd / "out" / str(test_no)
                test_wd.mkdir(parents=True, exist_ok=True)  # fresh directory

                print(
                    f"Testing #{test_no}: {test['onpass']} ({test['label']}) ... ",
                    end="",
                )

                content = {t["type"]: t["content"] for t in test["files"]}
                stdin = content.get(3, "")
                expected_stout = content.get(1, content.get(0, None))
                expected_sterr = content.get(2, None)

                out = subprocess.run(
                    ["make", "-s", "run"],
                    input=stdin,
                    cwd=wd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                )
                passed_test = True
                if expected_stout is not None and out.stdout != expected_stout:
                    print(fail("✗ Failed! (stdout) ---"))
                    print(out.stdout)
                    print("--- Output ^ --- v Expected ---")
                    print(expected_stout)
                    passed_test = False
                if expected_sterr is not None and out.stderr != expected_sterr:
                    print(fail("✗ Failed! (stderr) ---"))
                    print(out.stderr)
                    print("--- Output ^ --- v Expected ---")
                    print(expected_sterr)
                    passed_test = False
                if passed_test:
                    print(ok("✓ Passed!"))
                passed &= passed_test
                with open(test_wd / "stdout", "w") as f:
                    f.write(out.stdout)

                with open(test_wd / "stderr", "w") as f:
                    f.write(out.stderr)
        print("--", ok("✓ all tests passed") if passed else fail("✗ some tests failed"))
        return passed

    # --- Tests

    def dump_tests(self):
        wd = self.wd / "tests"

        rm_rf(wd)
        wd.mkdir()  # fresh directory

        for test_no, entry in enumerate(self.obj["tests"]["tests"]):
            path = wd / str(test_no)
            path.mkdir()

            for file in entry["files"]:
                try:
                    with open(path / FILETYPE_NAMES[file["type"]], "w") as f:
                        f.write(file["content"])
                except KeyError:
                    import ipdb

                    ipdb.set_trace()
                    import sys

                    sys.exit(1)

            with open(path / "test.yaml", "w") as f:
                entry = {**entry}
                del entry["files"]
                yaml.dump(entry, f, width=60)

    def load_tests(self):
        wd = self.wd / "tests"

        self.obj["tests"]["tests"] = []

        for test_no, path in enumerate(sorted(glob.glob(f"{wd}/*"))):

            with open(path + "/test.yaml") as f:
                test = yaml.safe_load(f)
            test["files"] = []

            for fname in glob.glob(f"{path}/*"):
                if "yaml" in fname:
                    continue  # not an output file
                file = {}
                with open(fname) as f:
                    file["content"] = f.read()

                file["type"] = FILETYPE_NOS[Path(fname).name]
                test["files"].append(file)

            self.obj["tests"]["tests"].append(test)

    # --- Workspace

    def dump_workspace(self):
        dump_one_workspace(self.obj["workspace"], self.wd / "workspace")

    def load_workspace(self):
        self.obj["workspace"] = load_one_workspace(
            self.wd / "workspace", self.obj["workspace"]
        )

    # --- Solutions

    def dump_solutions(self):
        for i, solution in enumerate(self.obj["solutions"]):
            dump_one_workspace(solution, self.wd / "solutions" / str(i))

    def load_solutions(self):
        old_solutions = self.obj["solutions"]
        self.obj["solutions"] = []
        for i, path in enumerate(glob.glob(f"{self.wd}/solutions/*")):
            old_solution = None if i >= len(old_solutions) else old_solutions[i]
            self.obj["solutions"].append(load_one_workspace(path, old_solution))

    # --- JSON

    @property
    def json_path(self):
        json_paths = glob.glob(f"{self.wd}/*.json")
        assert len(json_paths) == 1
        path = Path(json_paths[0])
        self.slug = path.stem
        return path

    def diff_json(self):
        old_json = load_problem_json(self.json_path)
        print("diff:")
        print(
            json.dumps(
                diff(old_json, self.obj, syntax="symmetric", marshal=True),
                indent=4,
                sort_keys=True,
            )
        )

    def diff_yaml(self):
        yaml_txt = yaml.dump(self.obj, width=60).split("\n")
        old_json = load_problem_json(self.json_path)
        old_yaml_txt = yaml.dump(old_json, width=60).split("\n")
        print(
            dbg(
                "\n".join(
                    difflib.unified_diff(old_yaml_txt, yaml_txt, n=0, lineterm="")
                )
            )
        )

    def backup_json(self):
        old_json = load_problem_json(self.json_path)

        path = self.wd / "backups"
        path.mkdir(exist_ok=True)

        fname = path / f"{self.slug}-{old_json['updated_at']}.json"
        with open(fname, "w") as f:
            json.dump(old_json, f)
            print("Backed up to", fname)

    def load_json(self):
        if self.internal_json is not None:
            self.obj = load_problem_json(self.internal_json, as_file=False)
        else:
            self.obj = load_problem_json(self.json_path)

    def dump_json(self):
        # obj -> string for each attribute
        for k in KEYS_WITH_DUMPS_VALUES:
            self.obj[k] = json.dumps(self.obj[k])

        self.obj["updated_at"] = timestamp()

        with open(self.json_path, "w") as f:
            json.dump(self.obj, f)

    # --- yaml

    def dump_yaml(self):
        with open(self.wd / "problem.yaml", "w") as f:
            yaml.dump(self.obj, f, width=60)

    def load_yaml(self):
        with open(self.wd / "problem.yaml") as f:
            self.obj = yaml.safe_load(f)

    # --- Content (markdown)

    def dump_content(self):
        with open(self.wd / "content.md", "w") as f:
            content = re.sub(
                "^(#markdown)", f"# {self.obj['title']}", self.obj["content"]
            )
            f.write(content)

    def load_content(self):
        with open(self.wd / "content.md", "r") as f:
            content = f.read()
            self.obj["content"] = re.sub("^(# .*)", f"#markdown", content)

    # --- Solution notes (markdown)
    def dump_solution_notes(self):
        with open(self.wd / "solution_notes.md", "w") as f:
            solution = re.sub(
                "^(#markdown)",
                f"# {self.obj['title']} - Solution Notes",
                self.obj["notes"],
            )
            f.write(solution)

    def load_solution_notes(self):
        with open(self.wd / "solution_notes.md", "r") as f:
            solution = f.read()
            self.obj["notes"] = re.sub("^(# .*)", f"#markdown", solution)


def main():
    args = parse_args()

    if len(args.names) == 0:
        print("Using all problems in directory")
        problems = [Path(p) for p in glob.glob("Ex*")]
    else:
        problems = args.names

    for problem_name in problems:
        print(problem_name, "------")
        problem = Problem(problem_name)
        if args.d:
            print("Diffing problem", problem_name)
            problem.load_all()
        elif args.w:
            print(fail("Dumping problem " + problem_name + " if testing succeeds"))
            problem.dump()
        elif args.f:
            print(fail("Dumping problem " + problem_name))
            problem.dump(force=True)
        elif args.r:
            print("Loading problem", problem_name)
            problem.load()
            problem.test()
        else:
            problem.test()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Parse and test Grok problems\nExpects to be placed within problems directory"
    )

    parser.add_argument(
        "names", help="exercise names, eg: ex1.02", nargs="*", default=None
    )

    parser.add_argument(
        "-r", action="store_true", help="read json and overwrite local files"
    )

    parser.add_argument(
        "-w",
        action="store_true",
        help="write json (and backup current json), if testing succeeds",
    )

    parser.add_argument(
        "-f",
        action="store_true",
        help="force write json (and backup current json), ignoring testing",
    )

    parser.add_argument(
        "-d", action="store_true", help="diff only (json vs current work directory)"
    )

    args = parser.parse_args()

    return args


if __name__ == "__main__":
    main()
