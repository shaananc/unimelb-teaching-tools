#!/usr/bin/env python3
"""This script downloads information about the workshops/tutorials in a class, and also downloads information about the students, and stores both datasets in CSV files
This script is supplemented by config.ini, for which a sample is provided.
"""
from pathlib import Path
from rich.console import Console
from rich.traceback import install
import sys
import os
import pandas as pd

from pathlib import Path

sys.path.insert(0, str(Path(os.path.realpath(__file__)).parent.parent))
from utils import (  # pylint:disable=wrong-import-position
    get_section_info,
    logger,
)


MODULE_CONFIG_SECTION = "STUDENT"

install()


def make_student_df(row):
    s = pd.DataFrame.from_dict(row["students"])
    s["section"] = row["name"]
    s.set_index("id")
    return s


def main():
    logger.info("Getting Section Info...")
    section_info = get_section_info()

    logger.info("Dumping to ./sections.csv")
    sec_df = pd.DataFrame.from_dict(section_info)

    sec_df.set_index("name")

    csv_cols = list(sec_df.columns.values)
    csv_cols.remove("students")
    sec_df.to_csv("./sections.csv", columns=csv_cols)

    sec_df = sec_df[sec_df["name"].str.contains("Tutorial")]
    sec_series = sec_df[["name", "students"]].apply(make_student_df, axis=1)
    student_df = pd.concat(sec_series.to_list(), ignore_index=True)
    student_df.rename(
        columns={"integration_id": "sis_id", "id": "canvas_id"}, inplace=True
    )
    student_df.set_index("canvas_id", inplace=True)

    student_df.to_csv("./students.csv")


if __name__ == "__main__":
    main()
