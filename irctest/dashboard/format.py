import base64
import dataclasses
import gzip
import hashlib
import importlib
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
    Union,
)
import xml.etree.ElementTree as ET

from defusedxml.ElementTree import parse as parse_xml
import docutils.core

from .shortxml import Namespace

NETLIFY_CHAR_BLACKLIST = frozenset('":<>|*?\r\n#')
"""Characters not allowed in output filenames"""


HTML = Namespace("http://www.w3.org/1999/xhtml")


@dataclasses.dataclass
class CaseResult:
    module_name: str
    class_name: str
    test_name: str
    job: str
    success: bool
    skipped: bool
    system_out: Optional[str]
    details: Optional[str] = None
    type: Optional[str] = None
    message: Optional[str] = None

    def output_filename(self) -> str:
        test_name = self.test_name
        if len(test_name) > 50 or set(test_name) & NETLIFY_CHAR_BLACKLIST:
            # File name too long or otherwise invalid. This should be good enough:
            m = re.match(r"(?P<function_name>\w+?)\[(?P<params>.+)\]", test_name)
            assert m, "File name is too long but has no parameter."
            test_name = f'{m.group("function_name")}[{md5sum(m.group("params"))}]'
        return f"{self.job}_{self.module_name}.{self.class_name}.{test_name}.txt"


TK = TypeVar("TK")
TV = TypeVar("TV")


def md5sum(text: str) -> str:
    return base64.urlsafe_b64encode(hashlib.md5(text.encode()).digest()).decode()


def group_by(list_: Iterable[TV], key: Callable[[TV], TK]) -> Dict[TK, List[TV]]:
    groups: Dict[TK, List[TV]] = {}
    for value in list_:
        groups.setdefault(key(value), []).append(value)

    return groups


def iter_job_results(job_file_name: Path, job: ET.ElementTree) -> Iterator[CaseResult]:
    (suite,) = job.getroot()
    for case in suite:
        if "name" not in case.attrib:
            continue

        success = True
        skipped = False
        details = None
        system_out = None
        extra: Dict[str, str] = {}
        for child in case:
            if child.tag == "skipped":
                success = True
                skipped = True
                details = None
                extra = child.attrib
            elif child.tag in ("failure", "error"):
                success = False
                skipped = False
                details = child.text
                extra = child.attrib
            elif child.tag == "system-out":
                assert (
                    system_out is None
                    # for some reason, skipped tests have two system-out;
                    # and the second one contains test teardown
                    or child.text.startswith(system_out.rstrip())
                ), ("Duplicate system-out tag", repr(system_out), repr(child.text))
                system_out = child.text
            else:
                assert False, child

        (module_name, class_name) = case.attrib["classname"].rsplit(".", 1)
        m = re.match(
            r"(.*/)?pytest[ -]results[ _](?P<name>.*)"
            r"[ _][(]?(stable|release|devel|devel_release)[)]?/pytest.xml(.gz)?",
            str(job_file_name),
        )
        assert m, job_file_name
        yield CaseResult(
            module_name=module_name,
            class_name=class_name,
            test_name=case.attrib["name"],
            job=m.group("name"),
            success=success,
            skipped=skipped,
            details=details,
            system_out=system_out,
            **extra,
        )


def rst_to_element(s: str) -> ET.Element:
    html = docutils.core.publish_parts(s, writer_name="xhtml")["html_body"]

    # Force the HTML namespace on all elements produced by docutils, which are
    # unqualified
    tree_builder = ET.TreeBuilder(
        element_factory=lambda tag, attrib: ET.Element(
            "{%s}%s" % (HTML.uri, tag),
            {"{%s}%s" % (HTML.uri, k): v for (k, v) in attrib.items()},
        )
    )
    parser = ET.XMLParser(target=tree_builder)

    htmltree = ET.fromstring(html, parser=parser)
    return htmltree


def docstring(obj: object) -> Optional[ET.Element]:
    if obj.__doc__ is None:
        return None

    return rst_to_element(obj.__doc__)


def build_job_html(job: str, results: List[CaseResult]) -> ET.Element:
    jobs = sorted({result.job for result in results})

    table = build_test_table(jobs, results, "job-results test-matrix")

    return HTML.html(
        HTML.head(
            HTML.title(job),
            HTML.link(rel="stylesheet", type="text/css", href="./style.css"),
        ),
        HTML.body(
            HTML.h1(job),
            table,
        ),
    )


def build_module_html(
    jobs: List[str], results: List[CaseResult], module_name: str
) -> ET.Element:
    module = importlib.import_module(module_name)

    table = build_test_table(jobs, results, "module-results test-matrix")

    return HTML.html(
        HTML.head(
            HTML.title(module_name),
            HTML.link(rel="stylesheet", type="text/css", href="./style.css"),
        ),
        HTML.body(
            HTML.h1(module_name),
            docstring(module),
            table,
        ),
    )


def build_test_table(
    jobs: List[str], results: List[CaseResult], class_: str
) -> ET.Element:
    multiple_modules = len({r.module_name for r in results}) > 1
    results_by_module_and_class = group_by(
        results, lambda r: (r.module_name, r.class_name)
    )

    job_row = HTML.tr(
        HTML.th(),  # column of case name
        [HTML.th(HTML.div(HTML.span(job)), {"class": "job-name"}) for job in jobs],
    )

    rows = []

    for (module_name, class_name), class_results in sorted(
        results_by_module_and_class.items()
    ):
        if multiple_modules:
            # if the page shows classes from various modules, use the fully-qualified
            # name in order to disambiguate and be clearer (eg. show
            # "irctest.server_tests.extended_join.MetadataTestCase" instead of just
            # "MetadataTestCase" which looks like it's about IRCv3's METADATA spec.
            qualified_class_name = f"{module_name}.{class_name}"
        else:
            # otherwise, it's not needed, so let's not display it
            qualified_class_name = class_name

        module = importlib.import_module(module_name)

        # Header row: class name
        row_anchor = f"{qualified_class_name}"
        rows.append(
            HTML.tr(
                HTML.th(
                    HTML.h2(
                        HTML.a(
                            qualified_class_name,
                            href=f"#{row_anchor}",
                            id=row_anchor,
                        ),
                    ),
                    docstring(getattr(module, class_name)),
                    colspan=str(len(jobs) + 1),
                )
            )
        )

        # Header row: one column for each implementation
        rows.append(job_row)

        # One row for each test:
        results_by_test = group_by(class_results, key=lambda r: r.test_name)
        for test_name, test_results in sorted(results_by_test.items()):
            row_anchor = f"{qualified_class_name}.{test_name}"
            if len(row_anchor) >= 50:
                # Too long; give up on generating readable URL
                # TODO: only hash test parameter
                row_anchor = md5sum(row_anchor)

            row = HTML.tr(
                HTML.th(
                    HTML.a(test_name, href=f"#{row_anchor}"), {"class": "test-name"}
                ),
                id=row_anchor,
            )
            rows.append(row)

            results_by_job = group_by(test_results, key=lambda r: r.job)
            for job_name in jobs:
                try:
                    (result,) = results_by_job[job_name]
                except KeyError:
                    row.append(HTML.td("d", {"class": "deselected"}))
                    continue

                text: Union[str, None, ET.Element]
                attrib = {}

                if result.skipped:
                    attrib["class"] = "skipped"
                    if result.type == "pytest.skip":
                        text = "s"
                    elif result.type == "pytest.xfail":
                        text = "X"
                        attrib["class"] = "expected-failure"
                    else:
                        text = result.type
                elif result.success:
                    attrib["class"] = "success"
                    if result.type:
                        # dead code?
                        text = result.type
                    else:
                        text = "."
                else:
                    attrib["class"] = "failure"
                    if result.type:
                        # dead code?
                        text = result.type
                    else:
                        text = "f"

                if result.system_out:
                    # There is a log file; link to it.
                    text = HTML.a(text or "?", href=f"./{result.output_filename()}")
                else:
                    text = text or "?"
                if result.message:
                    attrib["title"] = result.message

                row.append(HTML.td(text, attrib))

    return HTML.table(*rows, {"class": class_})


def write_html_pages(
    output_dir: Path, results: List[CaseResult]
) -> List[Tuple[str, str, str]]:
    """Returns the list of (module_name, file_name)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results_by_module = group_by(results, lambda r: r.module_name)

    # used as columns
    jobs = list(sorted({r.job for r in results}))

    job_categories = {}
    for job in jobs:
        is_client = any(
            "client_tests" in result.module_name and result.job == job
            for result in results
        )
        is_server = any(
            "server_tests" in result.module_name and result.job == job
            for result in results
        )
        assert is_client != is_server, (job, is_client, is_server)
        if job.endswith(("-atheme", "-anope", "-dlk")):
            assert is_server
            job_categories[job] = "server-with-services"
        elif is_server:
            job_categories[job] = "server"  # with or without services
        else:
            assert is_client
            job_categories[job] = "client"

    pages = []

    for module_name, module_results in sorted(results_by_module.items()):
        # Filter out client jobs if this is a server test module, and vice versa
        module_categories = {
            job_categories[result.job]
            for result in results
            if result.module_name == module_name and not result.skipped
        }

        module_jobs = [job for job in jobs if job_categories[job] in module_categories]

        root = build_module_html(module_jobs, module_results, module_name)
        file_name = f"{module_name}.xhtml"
        write_xml_file(output_dir / file_name, root)
        pages.append(("module", module_name, file_name))

    for category in ("server", "client"):
        for job in [job for job in job_categories if job_categories[job] == category]:
            job_results = [
                result
                for result in results
                if result.job == job or result.job.startswith(job + "-")
            ]
            root = build_job_html(job, job_results)
            file_name = f"{job}.xhtml"
            write_xml_file(output_dir / file_name, root)
            pages.append(("job", job, file_name))

    return pages


def write_test_outputs(output_dir: Path, results: List[CaseResult]) -> None:
    """Writes stdout files of each test."""
    for result in results:
        if result.system_out is None:
            continue
        output_file = output_dir / result.output_filename()
        with output_file.open("wt") as fd:
            fd.write(result.system_out)


def write_html_index(output_dir: Path, pages: List[Tuple[str, str, str]]) -> None:
    module_pages = []
    job_pages = []
    for page_type, title, file_name in sorted(pages):
        if page_type == "module":
            module_pages.append((title, file_name))
        elif page_type == "job":
            job_pages.append((title, file_name))
        else:
            assert False, page_type

    page = HTML.html(
        HTML.head(
            HTML.title("irctest dashboard"),
            HTML.link(rel="stylesheet", type="text/css", href="./style.css"),
        ),
        HTML.body(
            HTML.h1("irctest dashboard"),
            HTML.h2("Tests by command/specification"),
            HTML.dl(
                {"class": "module-index"},
                [
                    (
                        HTML.dt(HTML.a(module_name, href=f"./{file_name}")),
                        HTML.dd(docstring(importlib.import_module(module_name))),
                    )
                    for module_name, file_name in sorted(module_pages)
                ],
            ),
            HTML.h2("Tests by implementation"),
            HTML.ul(
                {"class": "job-index"},
                [
                    HTML.li(HTML.a(job, href=f"./{file_name}"))
                    for job, file_name in sorted(job_pages)
                ],
            ),
        ),
    )

    write_xml_file(output_dir / "index.xhtml", page)


def write_assets(output_dir: Path) -> None:
    css_path = output_dir / "style.css"
    source_css_path = Path(__file__).parent / "style.css"
    with css_path.open("wt") as fd:
        with source_css_path.open() as source_fd:
            fd.write(source_fd.read())


def write_xml_file(filename: Path, root: ET.Element) -> None:
    # Serialize
    if sys.version_info >= (3, 8):
        s = ET.tostring(root, default_namespace=HTML.uri)
    else:
        # default_namespace not supported
        s = ET.tostring(root)

    with filename.open("wb") as fd:
        fd.write(s)


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
        for result in iter_job_results(filename, parse_xml_file(filename))
    ]

    pages = write_html_pages(output_path, results)

    write_html_index(output_path, pages)
    write_test_outputs(output_path, results)
    write_assets(output_path)

    return 0


if __name__ == "__main__":
    (_, output_path, *filenames) = sys.argv
    exit(main(Path(output_path), list(map(Path, filenames))))
