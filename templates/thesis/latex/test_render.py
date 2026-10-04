"""Synthetic checks for the structured thesis-to-template mapping."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from render import math_source, reference_text, render


class ThesisRendererTests(unittest.TestCase):
    def test_math_and_references_reject_executable_or_missing_targets(self) -> None:
        self.assertEqual(math_source(r"E=mc^{2}"), r"E=mc^{2}")
        with self.assertRaises(ValueError):
            math_source(r"\input{/tmp/private}")
        with self.assertRaises(ValueError):
            reference_text("见{{eq:missing}}", {"eq": set(), "fig": set(), "cite": set()})
        with self.assertRaises(ValueError):
            reference_text("见{{cite:broken key}}", {"eq": set(), "fig": set(), "cite": set()})

    def test_synthetic_draft_reuses_template_and_semantic_numbering(self) -> None:
        document = {
            "metadata": {"title": "合成%论文", "student_name": "测试同学", "student_id": "00000001", "college": "合成学院", "major": "测试专业", "advisor": "测试导师"},
            "thesis": {"englishTitle": "Synthetic thesis", "submissionDate": "2026-05-01", "abstractCn": ["合成摘要"], "keywordsCn": "排版", "abstractEn": ["Synthetic abstract"], "keywordsEn": "layout", "chapters": [{"id": "chapter-a", "level": 1, "title": "绪论", "body": ["公式见{{eq:eq-aaaaaaaa}}，引用{{cite:sample2026}}。", {"type": "equation", "id": "eq-aaaaaaaa", "latex": r"E=mc^{2}"}]}], "referencesBibtex": "@article{sample2026,author={Test, Alice},title={Synthetic Research},journal={Synthetic Journal},year={2026}}", "acknowledgements": ["感谢"], "appendix": []},
        }
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "out"
            output.mkdir()
            render(document, output, Path(temp), False)
            info = (output / "content/info.tex").read_text(encoding="utf-8")
            body = (output / "content/content.tex").read_text(encoding="utf-8")
            self.assertIn(r"合成\%论文", info)
            self.assertIn(r"\section{绪论}", body)
            self.assertIn(r"\eqref{eq:eq-aaaaaaaa}", body)
            self.assertIn(r"\cite{sample2026}", body)
            self.assertIn(r"\begin{equation}", body)
            self.assertNotIn("郭小侠", "".join(path.read_text(encoding="utf-8") for path in (output / "content").glob("*.tex")))


if __name__ == "__main__":
    unittest.main()
