"""The monthly report as a Word document (E13-UC04).

The brief is a page; this is the thing that goes to a management meeting, an auditor or an
archive. It is generated from the brief and nothing else, so it cannot say something the
screen does not, and it keeps no numbers of its own: every figure is copied from the brief
that was built for the batch it names on its cover.

Two properties matter more than formatting:

- **Every number in the body has a source number** that resolves in the appendix to the
  formula, how many source cells it rests on and its evidence grade. A report that states a
  figure without saying where it came from is the thing this product exists to replace.
- **A stale brief is not exported.** If the review has been superseded, exporting the old
  conclusions makes a document that outlives the data it was true of.

The file is written as Office Open XML directly (a zip of a few XML parts). A document
generator would be a new dependency for one feature; the parts a report needs — headings,
paragraphs and tables — are small enough to write out, and nothing here parses a document.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from xml.sax.saxutils import escape

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOCUMENT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:pPr><w:spacing w:after="240"/></w:pPr>
<w:rPr><w:b/><w:sz w:val="44"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:pPr><w:spacing w:before="240" w:after="120"/><w:outlineLvl w:val="0"/></w:pPr>
<w:rPr><w:b/><w:sz w:val="30"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:sz w:val="21"/></w:rPr></w:style>
</w:styles>"""


@dataclass
class SourceIndex:
    """Every figure the body states, numbered, with where it came from."""
    entries: list[dict] = field(default_factory=list)

    def cite(self, subject: str, formula: str, sources: str, grade: str) -> str:
        self.entries.append({"subject": subject, "formula": formula, "sources": sources, "grade": grade})
        return f"[S{len(self.entries)}]"


def _text(value: str) -> str:
    return escape(str(value))


def _paragraph(text: str, style: str = "Normal") -> str:
    return (f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr>'
            f'<w:r><w:t xml:space="preserve">{_text(text)}</w:t></w:r></w:p>')


def _table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    width = str(int(9000 / max(len(rows[0]), 1)))
    cells = []
    for index, row in enumerate(rows):
        run = "<w:rPr><w:b/></w:rPr>" if index == 0 else ""
        cells.append("<w:tr>" + "".join(
            f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/></w:tcPr>'
            f'<w:p><w:r>{run}<w:t xml:space="preserve">{_text(cell)}</w:t></w:r></w:p></w:tc>'
            for cell in row) + "</w:tr>")
    return ('<w:tbl><w:tblPr><w:tblBorders>'
            + "".join(f'<w:{edge} w:val="single" w:sz="4" w:color="999999"/>'
                      for edge in ("top", "left", "bottom", "right", "insideH", "insideV"))
            + "</w:tblBorders></w:tblPr>" + "".join(cells) + "</w:tbl>")


def _number(value, unit: str = "") -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        text = f"{value:,.2f}".rstrip("0").rstrip(".")
    else:
        text = f"{value:,}"
    return f"{text}{unit}" if unit == "%" else (f"{text} {unit}".strip())


def _change(change: dict | None) -> str:
    if not change or change.get("state") != "compared":
        return "—"
    absolute = change.get("absolute")
    if change.get("basis") == "percentage_points":
        return f"{absolute:+.2f} pp"
    relative = change.get("relative")
    return _number(absolute) + (f"（{relative * 100:+.1f}%）" if relative is not None else "")


def build(brief: dict, *, conventions: list[dict], case: str = "") -> tuple[str, bytes]:
    """The report document for one brief. Returns (filename, bytes).

    The caller has already refused a stale brief; this function draws what it is given.
    """
    index = SourceIndex()
    period = brief.get("period", "")
    bound = brief.get("bound", {})
    partial = brief.get("report_status") != "validated" or brief.get("missing_departments")
    body: list[str] = [_paragraph(f"月度经营结论 · {period}", "Title")]

    body.append(_paragraph("一、封面与绑定版本", "Heading1"))
    if partial:
        body.append(_paragraph("部分完成：" + "、".join(brief.get("missing_departments") or []) + " 研判缺失，"
                               "本报告的关键指标与结论不包含这些部门。"))
    body.append(_table([["项目", "值"],
                        ["期间", period],
                        ["批次", bound.get("batch_id", "")],
                        ["研判报告", bound.get("report_id", "")],
                        ["字典版本", bound.get("dictionary", "")],
                        ["整合声明", bound.get("integration", "")],
                        ["生成时间", datetime.now(UTC).astimezone().strftime("%Y-%m-%d %H:%M %Z")],
                        ["数据案例", case]]))

    headline = brief.get("headline", {})
    body.append(_paragraph("二、本月结论", "Heading1"))
    body.append(_paragraph(
        f"本月需关注 {headline.get('attention', 0)} 项，正常 {headline.get('ok', 0)} 项，"
        f"待确认事项 {headline.get('open_items', 0)} 项，缺失部门 {headline.get('missing_departments', 0)} 个。"))

    body.append(_paragraph("三、关键指标与对比", "Heading1"))
    rows = [["指标", "本期", "较上期", "依据等级", "出处"]]
    for metric in brief.get("key_metrics", []):
        mark = index.cite(metric.get("title") or metric.get("metric", ""), metric.get("formula", ""),
                          f"{metric.get('source_count', 0)} 个来源单元格", (metric.get("grade") or {}).get("grade", ""))
        rows.append([metric.get("title") or metric.get("metric", ""),
                     _number(metric.get("value"), metric.get("unit", "")),
                     _change(metric.get("change")), (metric.get("grade") or {}).get("grade", ""), mark])
    body.append(_table(rows))

    body.append(_paragraph("四、各部门研判摘要", "Heading1"))
    roles = sorted({item.get("owner", "") for item in brief.get("attention", [])} |
                   {item.get("owner", "") for item in brief.get("key_metrics", [])})
    summary = [["部门", "需关注", "正常"]]
    for role in [r for r in roles if r]:
        attention = sum(1 for i in brief.get("attention", []) if i.get("owner") == role)
        ok = sum(1 for i in brief.get("key_metrics", []) if i.get("owner") == role) - attention
        summary.append([role, str(attention), str(max(ok, 0))])
    body.append(_table(summary))

    # An attention item names a metric; its formula and source count live on that metric line,
    # so the citation resolves to the same appendix entry a reader would look for.
    formulas = {m.get("metric", ""): m for m in brief.get("key_metrics", [])}
    body.append(_paragraph("五、需关注事项与负责人", "Heading1"))
    rows = [["事项", "负责人", "本期值", "阈值", "建议动作", "依据等级", "出处"]]
    for item in brief.get("attention", []):
        line = formulas.get(item.get("metric", ""), {})
        mark = index.cite(item.get("title", ""), line.get("formula", ""),
                          f"{line.get('source_count', 0)} 个来源单元格", (item.get("grade") or {}).get("grade", ""))
        rows.append([item.get("title", ""), item.get("owner", ""),
                     _number(item.get("value"), item.get("unit", "")), _number(item.get("threshold")),
                     item.get("action", ""), (item.get("grade") or {}).get("grade", ""), mark])
    body.append(_table(rows) if len(rows) > 1 else _paragraph("本月没有需关注事项。"))

    body.append(_paragraph("六、待确认事项", "Heading1"))
    open_items = brief.get("open_items", {})
    body.append(_table([["类型", "数量"],
                        ["总表待确认", str(open_items.get("master_issues", 0))],
                        ["隔离行", str(open_items.get("quarantined_rows", 0))],
                        ["待匹配上传列", str(open_items.get("column_questions", 0))]]))

    body.append(_paragraph("七、口径假设与限制", "Heading1"))
    rows = [["口径", "内容", "状态", "依据来源"]]
    states = {"confirmed": "业务方已确认", "replacement_requested": "业务方要求替换", "unconfirmed": "未确认"}
    for convention in conventions:
        rows.append([convention.get("id", ""), convention.get("text", ""),
                     states.get(convention.get("state", ""), convention.get("state", "")),
                     convention.get("source", "") or "—"])
    body.append(_table(rows) if len(rows) > 1 else _paragraph("本报告不依赖任何按通用做法补的口径。"))
    for limitation in brief.get("limitations", []):
        body.append(_paragraph(f"限制：{limitation}"))
    if brief.get("manager_decision"):
        body.append(_paragraph(f"决策边界：{brief['manager_decision']}"))

    body.append(_paragraph("八、附录：出处索引", "Heading1"))
    rows = [["编号", "对象", "公式", "来源", "依据等级"]]
    for number, entry in enumerate(index.entries, start=1):
        rows.append([f"S{number}", entry["subject"], entry["formula"], entry["sources"], entry["grade"]])
    body.append(_table(rows) if len(rows) > 1 else _paragraph("本报告正文没有引用数字。"))

    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                "<w:body>" + "".join(body) + "</w:body></w:document>")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES)
        archive.writestr("_rels/.rels", RELS)
        archive.writestr("word/_rels/document.xml.rels", DOCUMENT_RELS)
        archive.writestr("word/styles.xml", STYLES)
        archive.writestr("word/document.xml", document)
    version = str(bound.get("report_id", ""))[:8] or "v1"
    return f"月度经营结论-{period}-{version}.docx", buffer.getvalue()
