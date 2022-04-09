import base64
import dataclasses
import gzip
import hashlib
from pathlib import Path
import re
import sys
from typing import (
    IO,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    TypeVar,
)
import xml.etree.ElementTree as ET

from defusedxml.ElementTree import parse as parse_xml


@dataclasses.dataclass
class CaseResult:
    module_name: str
    class_name: str
    test_name: str
    job: str
    success: bool
    skipped: bool
    details: Optional[str] = None
    type: Optional[str] = None
    message: Optional[str] = None


TK = TypeVar("TK")
TV = TypeVar("TV")


def group_by(list_: Iterable[TV], key: Callable[[TV], TK]) -> Dict[TK, List[TV]]:
    groups: Dict[TK, List[TV]] = {}
    for value in list_:
        groups.setdefault(key(value), []).append(value)

    return groups


def iter_job_results(job_name: str, job: ET.ElementTree) -> Iterator[CaseResult]:
    (suite,) = job.getroot()
    for case in suite:
        if "name" not in case.attrib:
            continue

        if len(case):
            (case_result,) = case
            if case_result.tag == "skipped":
                success = True
                skipped = True
                details = None
            elif case_result.tag in ("failure", "error"):
                success = False
                skipped = False
                details = case_result.text
            else:
                assert False, case_result.tag
            extra = case_result.attrib
        else:
            success = True
            skipped = False
            details = None
            extra = {}

        (module_name, class_name) = case.attrib["classname"].rsplit(".", 1)
        m = re.match(
            r"pytest[ _]results[ _](?P<name>.*)"
            r"[ _][(]?(stable|release|devel|devel_release)[)]?.xml(.gz)?",
            job_name,
        )
        assert m, job_name
        yield CaseResult(
            module_name=module_name,
            class_name=class_name,
            test_name=case.attrib["name"],
            job=m.group("name"),
            success=success,
            skipped=skipped,
            details=details,
            **extra,
        )


def build_module_html(
    jobs: List[str], results: List[CaseResult], module_name: str
) -> ET.ElementTree:
    root = ET.Element("html")
    head = ET.SubElement(root, "head")
    ET.SubElement(head, "title").text = module_name

    body = ET.SubElement(root, "body")

    ET.SubElement(body, "h1").text = module_name

    results_by_class = group_by(results, lambda r: r.class_name)

    table = ET.SubElement(body, "table")

    job_row = ET.Element("tr")
    ET.SubElement(job_row, "th")  # column of case name
    for job in jobs:
        cell = ET.SubElement(job_row, "th")
        cell.text = job

    for (class_name, class_results) in results_by_class.items():
        # Header row: class name
        header_row = ET.SubElement(table, "tr")
        th = ET.SubElement(header_row, "th", colspan=str(len(jobs) + 1))
        row_anchor = f"{module_name}.{class_name}"
        section_header = ET.SubElement(
            ET.SubElement(th, "h2"),
            "a",
            href=f"#{row_anchor}",
            id=row_anchor,
        )
        section_header.text = class_name

        # Header row: one column for each implementation
        table.append(job_row)

        # One row for each test:
        results_by_test = group_by(class_results, key=lambda r: r.test_name)
        for (test_name, test_results) in results_by_test.items():
            row_anchor = f"{module_name}.{class_name}.{test_name}"
            if len(row_anchor) >= 50:
                # Too long; give up on generating readable URL
                # TODO: only hash test parameter
                row_anchor = base64.urlsafe_b64encode(
                    hashlib.md5(row_anchor.encode()).digest()
                ).decode()

            row = ET.SubElement(table, "tr", id=row_anchor)

            cell = ET.SubElement(row, "th")
            cell_link = ET.SubElement(cell, "a", href=f"#{row_anchor}")
            cell_link.text = test_name

            results_by_job = group_by(test_results, key=lambda r: r.job)
            for job_name in jobs:
                cell = ET.SubElement(row, "td")
                try:
                    (result,) = results_by_job[job_name]
                except KeyError:
                    cell.set("classes", "deselected")
                    cell.text = "d"
                    continue

                if result.skipped:
                    cell.set("classes", "skipped")
                    if result.type == "pytest.skip":
                        cell.text = "s"
                    else:
                        cell.text = result.type
                elif result.success:
                    cell.set("classes", "success")
                    if result.type:
                        # dead code?
                        cell.text = result.type
                    else:
                        cell.text = "."
                else:
                    cell.set("classes", "failure")
                    if result.type:
                        # dead code?
                        cell.text = result.type
                    else:
                        cell.text = "f"

    # Hacky: ET expects the namespace to be present in every tag we create instead;
    # but it would be excessively verbose.
    root.set("xmlns", "http://www.w3.org/1999/xhtml")

    return ET.ElementTree(root)


def write_html_pages(
    output_dir: Path, results: List[CaseResult]
) -> List[Tuple[str, str]]:
    """Returns the list of (module_name, file_name)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results_by_module = group_by(results, lambda r: r.module_name)

    # used as columns
    jobs = list(sorted({r.job for r in results}))

    pages = []

    for (module_name, module_results) in results_by_module.items():
        tree = build_module_html(jobs, module_results, module_name)
        file_name = f"{module_name}.xhtml"
        output_file = output_dir / file_name
        tree.write(str(output_file))
        pages.append((module_name, file_name))

    return pages


def write_html_index(output_dir: Path, pages: List[Tuple[str, str]]) -> None:
    root = ET.Element("html")
    head = ET.SubElement(root, "head")
    ET.SubElement(head, "title").text = "irctest dashboard"

    body = ET.SubElement(root, "body")

    ET.SubElement(body, "h1").text = "irctest dashboard"

    ul = ET.SubElement(body, "ul")

    for (module_name, file_name) in sorted(pages):
        link = ET.SubElement(ET.SubElement(ul, "li"), "a", href=f"./{file_name}")
        link.text = module_name

    root.set("xmlns", "http://www.w3.org/1999/xhtml")

    tree = ET.ElementTree(root)
    tree.write(str(output_dir / "index.xhtml"))


def parse_xml_file(filename: Path) -> ET.ElementTree:
    fd: IO
    if filename.suffix == ".gz":
        with gzip.open(filename, "rb") as fd:  # type: ignore
            return parse_xml(fd)  # type: ignore
    else:
        with open(filename) as fd:
            return parse_xml(fd)  # type: ignore


def main(output_path: Path, filenames: List[Path]) -> int:
    results = [
        result
        for filename in filenames
        for result in iter_job_results(filename.name, parse_xml_file(filename))
    ]

    pages = write_html_pages(output_path, results)

    write_html_index(output_path, pages)

    return 0


if __name__ == "__main__":
    (_, output_path, *filenames) = sys.argv
    exit(main(Path(output_path), list(map(Path, filenames))))
