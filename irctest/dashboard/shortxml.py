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
                [
                    (  # elements can be arbitrarily nested in lists
                        HTML.dt(HTML.a(title, href=f"./{title}.xhtml")),
                        HTML.dd(defintion),
                    )
                    for title, definition in sorted(definitions)
                ],
                class_="module-index",
            ),
            HTML.h2("Tests by implementation"),
            HTML.ul(
                [
                    HTML.li(HTML.a(job, href=f"./{file_name}"))
                    for job, file_name in sorted(job_pages)
                ],
                class_="job-index",
            ),
        ),
    )

    print(ET.tostring(page, default_namespace=HTML.uri))


Attributes can be passed either as dictionaries or as kwargs, and can be mixed
with child elements.
Trailing underscores are stripped from attributes, which allows passing reserved
Python keywords (eg. ``class_`` instead of ``class``)

Attributes are always qualified, and share the namespace of the element they are
attached to.

Mixed content (elements containing both text and child elements) is not supported.
"""

from typing import Dict, Sequence, Union
import xml.etree.ElementTree as ET


def _namespacify(ns: str, s: str) -> str:
    return "{%s}%s" % (ns, s)


_Children = Union[None, Dict[str, str], ET.Element, Sequence["_Children"]]


class ElementFactory:
    def __init__(self, namespace: str, tag: str):
        self._tag = _namespacify(namespace, tag)
        self._namespace = namespace

    def __call__(self, *args: Union[str, _Children], **kwargs: str) -> ET.Element:
        e = ET.Element(self._tag)

        attributes = {k.rstrip("_"): v for (k, v) in kwargs.items()}
        children = [*args, attributes]

        if args and isinstance(children[0], str):
            e.text = children[0]
            children.pop(0)

        for child in children:
            self._append_child(e, child)

        return e

    def _append_child(self, e: ET.Element, child: _Children) -> None:
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
