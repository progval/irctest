# Copyright (c) 2023 Valentin Lorentz
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""This module allows writing XML ASTs in a way that is more concise than the default
:mod:`xml.etree.ElementTree` interface.

For example:

.. code-block:: python

    from .shortxml import Namespace

    HTML = Namespace("http://www.w3.org/1999/xhtml")

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

    print(ET.tostring(page, default_namespace=HTML.uri))


Attributes can be passed either as dictionaries or as kwargs, and can be mixed
with child elements.

Attributes are always qualified, and share the namespace of the element they are
attached to.

Mixed content (elements containing both text and child elements) is not supported.
"""

from typing import Dict, Optional, Sequence, Union
import xml.etree.ElementTree as ET


def _namespacify(ns: str, s: str) -> str:
    return "{%s}%s" % (ns, s)


class ElementFactory:
    def __init__(self, namespace: str, tag: str):
        self._tag = _namespacify(namespace, tag)
        self._namespace = namespace

    def __call__(
        self,
        *args: Union[
            str,  # text
            None,
            ET.Element,
            Sequence[Union[None, ET.Element, Sequence[Optional[ET.Element]]]],
            Dict[str, str],  # attributes
        ],
        **kwargs: str,  # also attributes
    ) -> ET.Element:
        e = ET.Element(self._tag)

        children = [*args, kwargs]  # append attributes

        if args and isinstance(children[0], str):
            e.text = children[0]
            children.pop(0)

        for child in children:
            self._append_child(e, child)

        return e

    def _append_child(
        self,
        e: ET.Element,
        child: Union[
            str,
            None,
            ET.Element,
            Sequence[Union[None, ET.Element, Sequence[Optional[ET.Element]]]],
            Dict[str, str],
        ],
    ) -> None:
        if isinstance(child, ET.Element):
            e.append(child)
        elif child is None:
            pass
        elif isinstance(child, dict):
            for k, v in child.items():
                e.set(_namespacify(self._namespace, k), str(v))
        elif isinstance(child, str):
            raise ValueError("Mixed content is not supported")
        else:
            for grandchild in child:
                self._append_child(e, grandchild)


class Namespace:
    def __init__(self, uri: str):
        self.uri = uri

    def __getattr__(self, tag: str) -> ElementFactory:
        return ElementFactory(self.uri, tag)
