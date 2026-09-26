"""Assembles report context for the template and exports it to PDF."""
import io


def build_report_context(scenario, decision):
    report = decision.report_data()
    debate = scenario.debate.as_dict() if scenario.debate else {}

    return {
        "scenario": scenario,
        "decision": decision,
        "report": report,
        "plan": scenario.result_data("planner"),
        "finance": scenario.result_data("finance"),
        "marketing": scenario.result_data("marketing"),
        "operations": scenario.result_data("operations"),
        "risk": scenario.result_data("risk"),
        "debate": debate,
        "ceo": decision.ceo_data(),
    }


def generate_pdf_report(scenario, decision) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, ListFlowable, ListItem,
                                    PageBreak)

    ctx = build_report_context(scenario, decision)
    report = ctx["report"]
    plan = ctx["plan"]
    finance = ctx["finance"]
    risk = ctx["risk"]

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("BoardroomTitle", parent=styles["Title"],
                                 textColor=colors.HexColor("#6C5CE7"))
    h2 = ParagraphStyle("H2", parent=styles["Heading2"],
                        textColor=colors.HexColor("#8E7CFF"))
    body = styles["BodyText"]

    def esc(text):
        return (str(text or "-")
                .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    def table_block(rows, widths):
        t = Table(rows, colWidths=widths)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E7E2FF")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6D0FF")),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        return t

    def bullet_section(title, items):
        if not items:
            return
        story.append(Paragraph(title, h2))
        story.append(ListFlowable(
            [ListItem(Paragraph(esc(i), body)) for i in items if i], bulletType="bullet"))
        story.append(Spacer(1, 8))

    story = [
        Paragraph("Autonomous AI Boardroom — Executive Report", title_style),
        Spacer(1, 6),
        Paragraph(esc(scenario.title), styles["Heading3"]),
        Paragraph(f"Prepared {decision.created_at.strftime('%d %b %Y')} · "
                  f"Approver: {esc(decision.approver_role)}", body),
        Spacer(1, 12),

        Paragraph("Executive Summary", h2),
        Paragraph(esc(report.get("executive_summary")), body),
        Spacer(1, 10),

        Paragraph("Final Recommendation", h2),
        Paragraph(f"{esc(report.get('final_recommendation'))} "
                  f"(Strategic Score: {report.get('strategic_score', '-')}/100)", body),
        Paragraph(f"Sign-off status: {esc(decision.approval_label[0])}"
                  + (f" by {esc(decision.approved_by)}" if decision.approved_by else ""), body),
        Spacer(1, 10),
    ]

    # ---- Scores ----------------------------------------------------------
    scores = report.get("agent_scores", {}) or {}
    if scores:
        story.append(Paragraph("Agent Score Comparison", h2))
        rows = [["Agent", "Score / 100"]] + [
            [k.replace("_", " ").title(), v] for k, v in scores.items()]
        story.append(table_block(rows, [8 * cm, 4 * cm]))
        story.append(Spacer(1, 10))

    # ---- Plan ------------------------------------------------------------
    if plan and not plan.get("_failed"):
        story.append(Paragraph("Understood Request & Objective", h2))
        story.append(Paragraph(esc(plan.get("understood_request")), body))
        story.append(Paragraph(esc(plan.get("business_objective")), body))
        story.append(Spacer(1, 8))

        phases = plan.get("phases") or []
        if phases:
            story.append(Paragraph("Execution Plan — What, How and When", h2))
            rows = [["Phase", "What / How", "Start", "Months", "Owner"]]
            for p in phases[:8]:
                rows.append([
                    Paragraph(esc(p.get("phase")), body),
                    Paragraph(f"{esc(p.get('what_to_do'))}<br/><i>{esc(p.get('how_to_do_it'))}</i>", body),
                    f"M{int(p.get('start_month', 0))}",
                    str(p.get("duration_months", 1)),
                    Paragraph(esc(p.get("owner")), body),
                ])
            story.append(table_block(rows, [3.2 * cm, 7.5 * cm, 1.5 * cm, 1.5 * cm, 2.5 * cm]))
            story.append(Spacer(1, 10))

    # ---- Budget ----------------------------------------------------------
    budget = (finance.get("budget") or {}) if finance else {}
    if budget.get("items"):
        story.append(Paragraph("Budget Allocation", h2))
        rows = [["Category", "Share", "Amount (Rs.)"]]
        for item in budget["items"]:
            rows.append([item["category"], f"{item['percent']}%", f"{item['amount']:,.0f}"])
        rows.append(["TOTAL", "100%", f"{budget.get('total', 0):,.0f}"])
        story.append(table_block(rows, [7 * cm, 2.5 * cm, 4 * cm]))
        story.append(Spacer(1, 10))

    # ---- Projection ------------------------------------------------------
    projection = (finance.get("projection") or {}) if finance else {}
    if projection.get("rows"):
        story.append(Paragraph("Three-Year Projection", h2))
        rows = [["Year", "Revenue", "Operating Cost", "Profit", "Cumulative"]]
        for r in projection["rows"]:
            rows.append([r["year"], f"{r['revenue']:,.0f}", f"{r['operating_cost']:,.0f}",
                         f"{r['profit']:,.0f}", f"{r['cumulative_cashflow']:,.0f}"])
        story.append(table_block(rows, [2.5 * cm, 3.2 * cm, 3.5 * cm, 3 * cm, 3.3 * cm]))
        story.append(Paragraph(
            f"Payback: {esc(projection.get('payback_year') or 'not within the modelled horizon')}",
            body))
        story.append(Spacer(1, 10))

    story.append(PageBreak())

    # ---- Risk ------------------------------------------------------------
    matrix = (risk.get("matrix") or {}) if risk else {}
    if matrix.get("points"):
        story.append(Paragraph("Risk Register (highest exposure first)", h2))
        rows = [["Risk", "Category", "Severity", "Prob.", "Impact"]]
        for p in matrix["points"][:10]:
            rows.append([Paragraph(esc(p["risk"]), body), p["category"], p["severity"],
                         f"{p['probability']}%", f"{p['impact']}%"])
        story.append(table_block(rows, [7 * cm, 3 * cm, 2.2 * cm, 1.6 * cm, 1.7 * cm]))
        story.append(Spacer(1, 10))

    bullet_section("Key Opportunities", report.get("key_opportunities", []))
    bullet_section("Profit Drivers", report.get("profit_drivers", []))
    bullet_section("Loss Drivers", report.get("loss_drivers", []))
    bullet_section("Key Conflicts", report.get("conflicts", []))
    bullet_section("Resolutions", report.get("resolutions", []))
    bullet_section("Conditions Required for Approval", report.get("conditions", []))
    bullet_section("Action Plan", report.get("action_plan", []))
    bullet_section("First 90 Days", report.get("ninety_day_plan", []))
    bullet_section("What-If Insights", report.get("what_if_insights", []))

    story.append(Paragraph("CEO Reasoning", h2))
    story.append(Paragraph(esc(report.get("ceo_reasoning")), body))
    story.append(Spacer(1, 8))

    if decision.approval_note:
        story.append(Paragraph("Approver's Note", h2))
        story.append(Paragraph(esc(decision.approval_note), body))
        story.append(Spacer(1, 8))

    story.append(Paragraph("Final Conclusion", h2))
    story.append(Paragraph(esc(report.get("final_conclusion")), body))

    doc.build(story)
    buf.seek(0)
    return buf.read()
