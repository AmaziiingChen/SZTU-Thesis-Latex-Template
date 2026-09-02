"""Safe dual-route rendering for normalized process-document equations."""

from __future__ import annotations

from typing import Any

from docx.oxml import OxmlElement
from docx.oxml.ns import qn


GREEK_LATEX = {
    "α": r"\alpha", "β": r"\beta", "γ": r"\gamma", "δ": r"\delta",
    "ε": r"\epsilon", "ζ": r"\zeta", "η": r"\eta", "θ": r"\theta",
    "ι": r"\iota", "κ": r"\kappa", "λ": r"\lambda", "μ": r"\mu",
    "ν": r"\nu", "ξ": r"\xi", "ο": "o", "π": r"\pi", "ρ": r"\rho",
    "σ": r"\sigma", "τ": r"\tau", "υ": r"\upsilon", "φ": r"\phi",
    "χ": r"\chi", "ψ": r"\psi", "ω": r"\omega", "Γ": r"\Gamma",
    "Δ": r"\Delta", "Θ": r"\Theta", "Λ": r"\Lambda", "Ξ": r"\Xi",
    "Π": r"\Pi", "Σ": r"\Sigma", "Υ": r"\Upsilon", "Φ": r"\Phi",
    "Ψ": r"\Psi", "Ω": r"\Omega",
}
MATH_OPERATOR_LATEX = {
    "×": r"\times ", "·": r"\cdot ", "≤": r"\leq ", "≥": r"\geq ",
    "−": "-", "%": r"\%", " ": r"\,",
}


def _append_omml_children(parent, node: dict[str, Any]) -> None:
    node_type = node["type"]
    if node_type == "text":
        run = OxmlElement("m:r")
        text = OxmlElement("m:t")
        text.text = node["value"]
        run.append(text)
        parent.append(run)
        return
    if node_type == "row":
        for item in node["items"]:
            _append_omml_children(parent, item)
        return
    element_names = {
        "fraction": ("m:f", (("m:num", "numerator"), ("m:den", "denominator"))),
        "subscript": ("m:sSub", (("m:e", "base"), ("m:sub", "sub"))),
        "superscript": ("m:sSup", (("m:e", "base"), ("m:sup", "super"))),
        "square_root": ("m:rad", (("m:e", "body"),)),
    }
    element_name, children = element_names[node_type]
    element = OxmlElement(element_name)
    if node_type == "square_root":
        properties = OxmlElement("m:radPr")
        degree_hidden = OxmlElement("m:degHide")
        degree_hidden.set(qn("m:val"), "1")
        properties.append(degree_hidden)
        element.append(properties)
    for child_name, field in children:
        container = OxmlElement(child_name)
        _append_omml_children(container, node[field])
        element.append(container)
    parent.append(element)


def append_omml(paragraph, expression: dict[str, Any]) -> None:
    """Append a centered native Word equation to an existing paragraph."""
    math_para = OxmlElement("m:oMathPara")
    properties = OxmlElement("m:oMathParaPr")
    justification = OxmlElement("m:jc")
    justification.set(qn("m:val"), "center")
    properties.append(justification)
    math_para.append(properties)
    math = OxmlElement("m:oMath")
    _append_omml_children(math, expression)
    math_para.append(math)
    paragraph._p.append(math_para)


def _latex_text(value: str) -> str:
    return "".join(
        GREEK_LATEX.get(char, MATH_OPERATOR_LATEX.get(char, char)) for char in value
    )


def latex_math(node: dict[str, Any]) -> str:
    """Render normalized math AST to a command-injection-free LaTeX fragment."""
    node_type = node["type"]
    if node_type == "text":
        return _latex_text(node["value"])
    if node_type == "row":
        return "".join(latex_math(item) for item in node["items"])
    if node_type == "fraction":
        return rf"\frac{{{latex_math(node['numerator'])}}}{{{latex_math(node['denominator'])}}}"
    if node_type == "subscript":
        return rf"{{{latex_math(node['base'])}}}_{{{latex_math(node['sub'])}}}"
    if node_type == "superscript":
        return rf"{{{latex_math(node['base'])}}}^{{{latex_math(node['super'])}}}"
    if node_type == "square_root":
        return rf"\sqrt{{{latex_math(node['body'])}}}"
    raise AssertionError(f"unsupported normalized math node: {node_type}")
