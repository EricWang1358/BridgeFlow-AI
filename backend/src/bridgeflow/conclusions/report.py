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


#: The document's own wording in each interface language. The figures, names and formulas
#: inside are the brief's and stay as the declarations wrote them.
WORDS: dict[str, dict[str, str]] = {
    "zh": {
        "title": "月度经营结论 · {period}", "cover": "一、封面与绑定版本",
        "partial": "部分完成：{departments} 研判缺失，本报告的关键指标与结论不包含这些部门。", "join": "、",
        "item": "项目", "value": "值", "period": "期间", "batch": "批次", "review": "研判报告",
        "dictionary": "字典版本", "integration": "整合声明", "generated": "生成时间", "case": "数据案例",
        "headline": "二、本月结论",
        "headline_text": "本月需关注 {attention} 项，正常 {ok} 项，待确认事项 {open_items} 项，缺失部门 {missing} 个。",
        "metrics": "三、关键指标与对比", "metric": "指标", "current": "本期", "change": "较上期",
        "grade": "依据等级", "source": "出处", "sources": "{count} 个来源单元格",
        "roles": "四、各部门研判摘要", "department": "部门", "attention": "需关注", "ok": "正常",
        "attention_items": "五、需关注事项与负责人", "subject": "事项", "owner": "负责人", "threshold": "阈值",
        "action": "建议动作", "no_attention": "本月没有需关注事项。",
        "open": "六、待确认事项", "kind": "类型", "count": "数量", "master_issues": "总表待确认",
        "quarantined": "隔离行", "column_questions": "待匹配上传列",
        "conventions": "七、口径假设与限制", "convention": "口径", "content": "内容", "state": "状态",
        "basis": "依据来源", "confirmed": "业务方已确认", "replacement_requested": "业务方要求替换",
        "unconfirmed": "未确认", "no_conventions": "本报告不依赖任何按通用做法补的口径。",
        "limitation": "限制：{text}", "decision": "决策边界：{text}",
        "appendix": "八、附录：出处索引", "number": "编号", "object": "对象", "formula": "公式",
        "from": "来源", "no_sources": "本报告正文没有引用数字。", "relative": "（{relative}）",
        "filename": "月度经营结论-{period}-{version}.docx",
    },
    "en": {
        "title": "Monthly business conclusions · {period}", "cover": "1. Cover and bound versions",
        "partial": "Partial: the review is missing {departments}; the key metrics and conclusions here leave them out.",
        "join": ", ",
        "item": "Item", "value": "Value", "period": "Period", "batch": "Batch", "review": "Review report",
        "dictionary": "Dictionary version", "integration": "Integration declaration", "generated": "Generated",
        "case": "Data case",
        "headline": "2. This month's conclusions",
        "headline_text": "{attention} need attention, {ok} are normal, {open_items} open items, {missing} missing departments.",
        "metrics": "3. Key metrics and comparison", "metric": "Metric", "current": "This period",
        "change": "Change", "grade": "Evidence grade", "source": "Source", "sources": "{count} source cells",
        "roles": "4. Department review summary", "department": "Department", "attention": "Attention",
        "ok": "Normal",
        "attention_items": "5. Items needing attention and owners", "subject": "Item", "owner": "Owner",
        "threshold": "Threshold", "action": "Suggested action", "no_attention": "Nothing needs attention this month.",
        "open": "6. Open items", "kind": "Kind", "count": "Count", "master_issues": "Master open items",
        "quarantined": "Quarantined rows", "column_questions": "Uploaded columns to match",
        "conventions": "7. Conventions and limitations", "convention": "Convention", "content": "Content",
        "state": "State", "basis": "Basis", "confirmed": "Confirmed by the business",
        "replacement_requested": "Replacement requested by the business", "unconfirmed": "Unconfirmed",
        "no_conventions": "This report rests on no common-practice convention.",
        "limitation": "Limitation: {text}", "decision": "Decision boundary: {text}",
        "appendix": "8. Appendix: source index", "number": "No.", "object": "Subject", "formula": "Formula",
        "from": "Sources", "no_sources": "The body of this report cites no figures.", "relative": " ({relative})",
        "filename": "Monthly-conclusions-{period}-{version}.docx",
    },
}


def _change(change: dict | None, w: dict[str, str]) -> str:
    if not change or change.get("state") != "compared":
        return "—"
    absolute = change.get("absolute")
    if change.get("basis") == "percentage_points":
        return f"{absolute:+.2f} pp"
    relative = change.get("relative")
    return _number(absolute) + (w["relative"].format(relative=f"{relative * 100:+.1f}%") if relative is not None else "")


def build(brief: dict, *, conventions: list[dict], case: str = "", language: str = "zh") -> tuple[str, bytes]:
    """The report document for one brief, in the interface's language. Returns (filename, bytes).

    The caller has already refused a stale brief; this function draws what it is given.
    """
    w = WORDS.get(language, WORDS["zh"])
    index = SourceIndex()
    period = brief.get("period", "")
    bound = brief.get("bound", {})
    partial = brief.get("report_status") != "validated" or brief.get("missing_departments")
    body: list[str] = [_paragraph(w["title"].format(period=period), "Title")]

    body.append(_paragraph(w["cover"], "Heading1"))
    if partial:
        body.append(_paragraph(w["partial"].format(departments=w["join"].join(brief.get("missing_departments") or []))))
    body.append(_table([[w["item"], w["value"]],
                        [w["period"], period],
                        [w["batch"], bound.get("batch_id", "")],
                        [w["review"], bound.get("report_id", "")],
                        [w["dictionary"], bound.get("dictionary", "")],
                        [w["integration"], bound.get("integration", "")],
                        [w["generated"], datetime.now(UTC).astimezone().strftime("%Y-%m-%d %H:%M %Z")],
                        [w["case"], case]]))

    headline = brief.get("headline", {})
    body.append(_paragraph(w["headline"], "Heading1"))
    body.append(_paragraph(w["headline_text"].format(
        attention=headline.get("attention", 0), ok=headline.get("ok", 0),
        open_items=headline.get("open_items", 0), missing=headline.get("missing_departments", 0))))

    body.append(_paragraph(w["metrics"], "Heading1"))
    rows = [[w["metric"], w["current"], w["change"], w["grade"], w["source"]]]
    for metric in brief.get("key_metrics", []):
        mark = index.cite(metric.get("title") or metric.get("metric", ""), metric.get("formula", ""),
                          w["sources"].format(count=metric.get("source_count", 0)), (metric.get("grade") or {}).get("grade", ""))
        rows.append([metric.get("title") or metric.get("metric", ""),
                     _number(metric.get("value"), metric.get("unit", "")),
                     _change(metric.get("change"), w), (metric.get("grade") or {}).get("grade", ""), mark])
    body.append(_table(rows))

    body.append(_paragraph(w["roles"], "Heading1"))
    roles = sorted({item.get("owner", "") for item in brief.get("attention", [])} |
                   {item.get("owner", "") for item in brief.get("key_metrics", [])})
    summary = [[w["department"], w["attention"], w["ok"]]]
    for role in [r for r in roles if r]:
        attention = sum(1 for i in brief.get("attention", []) if i.get("owner") == role)
        ok = sum(1 for i in brief.get("key_metrics", []) if i.get("owner") == role) - attention
        summary.append([role, str(attention), str(max(ok, 0))])
    body.append(_table(summary))

    # An attention item names a metric; its formula and source count live on that metric line,
    # so the citation resolves to the same appendix entry a reader would look for.
    formulas = {m.get("metric", ""): m for m in brief.get("key_metrics", [])}
    body.append(_paragraph(w["attention_items"], "Heading1"))
    rows = [[w["subject"], w["owner"], w["current"], w["threshold"], w["action"], w["grade"], w["source"]]]
    for item in brief.get("attention", []):
        line = formulas.get(item.get("metric", ""), {})
        mark = index.cite(item.get("title", ""), line.get("formula", ""),
                          w["sources"].format(count=line.get("source_count", 0)), (item.get("grade") or {}).get("grade", ""))
        rows.append([item.get("title", ""), item.get("owner", ""),
                     _number(item.get("value"), item.get("unit", "")), _number(item.get("threshold")),
                     item.get("action", ""), (item.get("grade") or {}).get("grade", ""), mark])
    body.append(_table(rows) if len(rows) > 1 else _paragraph(w["no_attention"]))

    body.append(_paragraph(w["open"], "Heading1"))
    open_items = brief.get("open_items", {})
    body.append(_table([[w["kind"], w["count"]],
                        [w["master_issues"], str(open_items.get("master_issues", 0))],
                        [w["quarantined"], str(open_items.get("quarantined_rows", 0))],
                        [w["column_questions"], str(open_items.get("column_questions", 0))]]))

    body.append(_paragraph(w["conventions"], "Heading1"))
    rows = [[w["convention"], w["content"], w["state"], w["basis"]]]
    states = {state: w[state] for state in ("confirmed", "replacement_requested", "unconfirmed")}
    for convention in conventions:
        rows.append([convention.get("id", ""), convention.get("text", ""),
                     states.get(convention.get("state", ""), convention.get("state", "")),
                     convention.get("source", "") or "—"])
    body.append(_table(rows) if len(rows) > 1 else _paragraph(w["no_conventions"]))
    for limitation in brief.get("limitations", []):
        body.append(_paragraph(w["limitation"].format(text=limitation)))
    if brief.get("manager_decision"):
        body.append(_paragraph(w["decision"].format(text=brief["manager_decision"])))

    body.append(_paragraph(w["appendix"], "Heading1"))
    rows = [[w["number"], w["object"], w["formula"], w["from"], w["grade"]]]
    for number, entry in enumerate(index.entries, start=1):
        rows.append([f"S{number}", entry["subject"], entry["formula"], entry["sources"], entry["grade"]])
    body.append(_table(rows) if len(rows) > 1 else _paragraph(w["no_sources"]))

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
    return w["filename"].format(period=period, version=version), buffer.getvalue()
