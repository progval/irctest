"""
Reads pytest's XML output, and produces a report of the test run(s).
"""

import dataclasses
import functools
import itertools
import re
import sys
import textwrap
from typing import Optional, Set
import xml.etree.ElementTree as ET


def visit_bottomup(f, d):
    """Visits and rewrites a nested-dict ``d`` from the bottom to the top,
    using the ``f`` predicate."""
    if isinstance(d, dict):
        return f({k: visit_bottomup(f, v) for (k, v) in d.items()})
    else:
        return f(d)


@dataclasses.dataclass
class CaseResult:
    success: bool
    skipped: bool
    type: Optional[str] = None
    message: Optional[str] = None


@dataclasses.dataclass
class CompactedResult:
    success: bool
    count: int
    nb_skipped: int
    messages: Set[str]


def compact_results(d):
    """Rewrite the nested dict ``d`` of CaseResult in a more compact form;
    by folding successful subtrees."""
    if isinstance(d, dict):
        if set(d) == {None}:
            return d[None]
        if not all(isinstance(v, CompactedResult) for v in d.values()):
            # Some children are not compactable, so this subtree isn't either
            return d
        statuses = {v.success for v in d.values()}
        if len(statuses) == 1:
            (status,) = statuses
            return CompactedResult(
                success=status,
                count=sum(v.count for v in d.values()),
                nb_skipped=sum(v.nb_skipped for v in d.values()),
                messages=set(
                    itertools.chain.from_iterable(v.messages for v in d.values())
                ),
            )
        else:
            return d
    elif isinstance(d, CaseResult):
        return CompactedResult(
            success=d.success,
            count=1,
            nb_skipped=int(d.skipped),
            messages={d.message} if d.message else set(),
        )
    else:
        assert False, repr(d)


def format_results(d) -> str:
    """Using the nested dict ``d`` of CaseResult, formats a string report."""
    if isinstance(d, dict):
        items = [f"<li>{k}: {v}</li>" for (k, v) in d.items()]
        items_str = textwrap.indent("\n".join(items), prefix="  ")
        return f"<ul>\n{items_str}\n</ul>"
    elif isinstance(d, CompactedResult):
        if d.success:
            if d.nb_skipped:
                reason = "".join(f"<li>{msg}</li>" for msg in d.messages)
                return (
                    f"✔️ {d.count} successful, "
                    f"including {d.nb_skipped} skipped: <ul>{reason}</ul>"
                )
            else:
                return f"✔️ {d.count} successful"
        else:
            assert d.nb_skipped == 0
            reason = "".join(f"<li>{msg}</li>" for msg in d.messages)
            return f"❌ {d.count} failed: <ul>{reason}</ul>"
    else:
        assert False, d


def main(filenames):

    for filename in filenames:
        results = {}
        job = ET.parse(filename).getroot()
        (suite,) = job
        for case in suite:
            if "name" not in case.attrib:
                continue
            path = case.attrib["classname"].split(".")
            class_results = functools.reduce(
                lambda d, name: d.setdefault(name, {}),
                path,
                results.setdefault(filename, {}),
            )

            if len(case):
                (case_result,) = case
                if case_result.tag == "skipped":
                    leaf = CaseResult(success=True, skipped=True, **case_result.attrib)
                elif case_result.tag in ("failure", "error"):
                    leaf = CaseResult(
                        success=False, skipped=False, **case_result.attrib
                    )
                else:
                    assert False, case_result.tag
            else:
                leaf = CaseResult(success=True, skipped=False)

            name = case.attrib["name"]
            m = re.match(r"^(?P<name>.*?)\[(?P<param>.*)\]$", name)
            if m:
                d = class_results.setdefault(m.group("name"), {})
                assert m.group("param") not in d
                d[m.group("param")] = leaf
            else:
                d = class_results.setdefault(name, {})
                assert None not in d
                d[None] = leaf

        results = visit_bottomup(compact_results, results)
        print(visit_bottomup(format_results, results))


if __name__ == "__main__":
    (_, *filenames) = sys.argv
    exit(main(filenames))
