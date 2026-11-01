"""Render the 2027 cover and verify geometry, metadata, wrapping and body isolation."""
import json
import re
import subprocess
import sys
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[2]


def main():
    spec = json.loads((ROOT / "templates/thesis/spec/layout.json").read_text(encoding="utf-8"))["cover"]
    fixtures = json.loads((ROOT / "templates/thesis/fixtures/cover-2027.json").read_text(encoding="utf-8"))
    reports = []
    preamble = r"""\documentclass{SZTUthesis}
\graphicspath{{images/}}
\titleen{Synthetic Cover Test}
\author{合成学生}
\department{中德智能制造学院}
\priormajor{合成专业}
\studentid{TEST000001}
\supervisor{合成主导师}
\supervisortitle{不应出现的职称}
\thesisdate{year=2027,month=5,day=1}
"""
    for name, case in fixtures.items():
        folder = ROOT / "tmp/cover-2027-tests" / name
        folder.mkdir(parents=True, exist_ok=True)
        secondary = "" if case["secondary"] is None else r"\subsupervisor{" + case["secondary"] + "}\n"
        source = preamble + r"\titlecn{" + case["title"] + "}\n" + secondary + r"""\begin{document}
\special{pdf:minorversion 6}
\makecoverpage
\typeout{COVERTESTBODYWIDTH=\the\textwidth}
\section{正文页面校验}
这是独立的正文页面，用于检查封面没有改变正文布局。
\end{document}
"""
        (folder / "main.tex").write_text(source, encoding="utf-8")
        result = subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", "-no-shell-escape", "-output-directory=" + str(folder), str(folder / "main.tex")], cwd=ROOT, capture_output=True)
        (folder / "build.log").write_bytes(result.stdout + result.stderr)
        assert result.returncode == 0, (name, (folder / "build.log"))
        with pdfplumber.open(folder / "main.pdf") as pdf:
            assert len(pdf.pages) == 2, (name, len(pdf.pages))
            page = pdf.pages[0]
            text = re.sub(r"\s+", "", page.extract_text())
            assert "职称" not in text and "不应出现" not in text
            assert "合成主导师；合成副导师" in text if case["secondary"] else "合成主导师；" not in text
            assert "正文页面校验" not in text and "正文页面校验" in re.sub(r"\s+", "", pdf.pages[1].extract_text())
            label_chars = [c for c in page.chars if c["text"] == "姓" and c["top"] > 450]
            assert len(label_chars) == 1 and abs(label_chars[0]["x0"] - spec["fields"]["label_x"]) < 0.3
            assert abs(label_chars[0]["top"] - 489.28) < 0.4
            rules = [e for e in page.edges if e["orientation"] == "h" and abs(e["x0"] - spec["fields"]["value_left"]) < 0.2 and abs(e["width"] - spec["fields"]["value_width"]) < 0.2]
            assert len(rules) == 6, (name, rules)
            for index, rule in enumerate(sorted(rules, key=lambda e: e["top"])):
                expected = spec["fields"]["first_baseline"] + index * spec["fields"]["row_step"] + spec["fields"]["underline_offset"] - 0.24
                assert abs(rule["top"] - expected) < 0.3
            topic_chars = [c for c in page.chars if 295 < c["top"] < 480 and "KaiTi" in c["fontname"] and c["text"] != "："]
            cjk = [c for c in topic_chars if "\u4e00" <= c["text"] <= "\u9fff"]
            assert cjk and all(abs(c["size"] - 22) < 0.1 for c in cjk)
            rows = sorted(set(round(c["top"], 1) for c in cjk))
            for y in rows:
                row = [c for c in topic_chars if abs(c["top"] - y) < 0.3 and c["text"].strip()]
                assert abs((min(c["x0"] for c in row) + max(c["x1"] for c in row)) / 2 - spec["topic"]["center_x"]) < 3.5
            if name in {"wrapped", "explicit_break"}:
                assert len(rows) >= 2
            assert max(c["bottom"] for c in topic_chars) < 480
            logo = [e for e in page.curves + page.rects + page.chars if 110 < e["top"] < 190]
            assert logo
            assert abs(min(e["top"] for e in logo) - spec["logo"]["top"]) < 0.6
            assert abs(min(e["x0"] for e in logo) - spec["logo"]["left"]) < 0.6
            assert abs(max(e["x1"] for e in logo) - min(e["x0"] for e in logo) - spec["logo"]["width"]) < 0.6
            reports.append({"case": name, "pages": 2, "topic_lines": len(rows), "field_rows": len(rules)})
        log = (folder / "build.log").read_text(encoding="utf-8", errors="replace")
        width = float(re.search(r"COVERTESTBODYWIDTH=([0-9.]+)pt", log).group(1))
        assert abs(width - (210 - 31.7 * 2) * 72.27 / 25.4) < 0.2
    # Reject excessive content rather than overlap the fixed information rows.
    folder = ROOT / "tmp/cover-2027-tests/overflow"
    folder.mkdir(parents=True, exist_ok=True)
    source = preamble + r"\titlecn{" + "合成超长标题" * 30 + r"}\begin{document}\makecoverpage\end{document}"
    (folder / "main.tex").write_text(source, encoding="utf-8")
    result = subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", "-no-shell-escape", "-output-directory=" + str(folder), str(folder / "main.tex")], cwd=ROOT, capture_output=True)
    assert result.returncode != 0 and b"Title exceeds the official cover area" in result.stdout
    (ROOT / "tmp/cover-2027-tests/report.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    print("PASS: 2027 cover geometry, single/dual advisors, natural/explicit title wrapping, subscripts, overflow rejection, and body isolation")


if __name__ == "__main__":
    main()
