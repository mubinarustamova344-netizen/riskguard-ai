# -*- coding: utf-8 -*-
"""
Generates RiskGuard_AI_1400_Report.docx on the desktop — approx 1400 words.
Run: python write_1400_report.py
"""
import re
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUTPUT = r"c:\Users\rusta\Desktop\RiskGuard_AI_1400_Report.docx"
GITHUB = "https://github.com/mubinarustamova344-netizen/riskguard-ai"

doc = Document()
for section in doc.sections:
    section.top_margin    = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin   = Cm(3.0)
    section.right_margin  = Cm(2.5)

def heading(text, level=1):
    p = doc.add_heading(text, level=level)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT

def para(text, italic=False, size=11):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    run = p.add_run(text)
    run.italic = italic
    run.font.size = Pt(size)
    p.paragraph_format.space_after = Pt(6)

def bullet(text):
    p = doc.add_paragraph(text, style='List Bullet')
    if p.runs:
        p.runs[0].font.size = Pt(11)

def pb():
    doc.add_page_break()

def center(text, size=12, bold=False, italic=False):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)

def tbl_hdr(tbl, headers):
    row = tbl.rows[0]
    for i, hdr in enumerate(headers):
        cell = row.cells[i]
        cell.text = hdr
        if cell.paragraphs[0].runs:
            run = cell.paragraphs[0].runs[0]
            run.bold = True
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor(255, 255, 255)
        try:
            shd = OxmlElement('w:shd')
            shd.set(qn('w:val'), 'clear')
            shd.set(qn('w:color'), 'auto')
            shd.set(qn('w:fill'), '1E3A5F')
            cell._tc.get_or_add_tcPr().append(shd)
        except Exception:
            pass

def tbl_row(tbl, values):
    row = tbl.add_row()
    for i, val in enumerate(values):
        cell = row.cells[i]
        cell.text = str(val)
        if cell.paragraphs[0].runs:
            cell.paragraphs[0].runs[0].font.size = Pt(10)

# ════════════════════════════════════════════════════════════
# TITLE PAGE
# ════════════════════════════════════════════════════════════
doc.add_paragraph()
doc.add_paragraph()
center("PDP UNIVERSITY", 20, bold=True)
center("Faculty of Business Information Technology  ·  Tashkent, Uzbekistan", 11, italic=True)
doc.add_paragraph()
center("INDEPENDENT PROJECT REPORT", 14, bold=True)
center("Pearson BTEC Level 6 Diploma in Digital Technologies", 12)
center("Unit 2 — Unit Code: 70726U — Credit Value: 30", 11)
doc.add_paragraph()
center("RiskGuard AI", 18, bold=True)
center("A Machine Learning–Powered Road Accident Risk Assessment\nSystem for Motor Insurance", 14)
doc.add_paragraph()
center('"How can machine learning improve the accuracy, consistency and transparency\nof motor insurance risk assessment and premium pricing?"', 11, italic=True)
doc.add_paragraph()
for label, val in [
    ("Student Name:", "Mubina Rustamova"),
    ("Student ID:", "230277"),
    ("Programme:", "22-306 — Business Information Technology"),
    ("Supervisor:", "Xolmirzayev Muxammadjon"),
    ("Submission Date:", "08 June 2026"),
    ("GitHub:", GITHUB),
]:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = p.add_run(f"{label}  "); r1.bold = True; r1.font.size = Pt(11)
    r2 = p.add_run(val); r2.font.size = Pt(11)
pb()

# ════════════════════════════════════════════════════════════
# ABSTRACT  (~90 words)
# ════════════════════════════════════════════════════════════
heading("Abstract")
para(
    "This project investigates how machine learning can automate and improve motor insurance driver risk "
    "assessment. A synthetic dataset of 30,000 driver records was generated and used to train six "
    "classifiers. A tuned XGBoost model achieved the best result: 85.22% accuracy and ROC-AUC of 0.9738. "
    "The system was deployed as a secure Flask web application with risk score visualisation, premium "
    "calculation, per-factor explainability, an AI chatbot (RiskBot), and a bilingual English/Uzbek "
    "interface. Source code is publicly available at: " + GITHUB
)
para("Keywords: machine learning; motor insurance; risk assessment; XGBoost; explainable AI; Flask", italic=True)
pb()

# ════════════════════════════════════════════════════════════
# 1. INTRODUCTION  (~170 words)
# ════════════════════════════════════════════════════════════
heading("1. Introduction")
para(
    "Despite the rapid growth of machine learning (ML) tools, many motor insurers — especially in Central "
    "Asia — still rely on simple demographic variables and manual multipliers to price risk. The Association "
    "of British Insurers (ABI, 2023) reported that motor insurance claims in the UK reached £6.7 billion in "
    "2023, with fraud losses accounting for £1.1 billion. McKinsey and Company (2023) estimate that "
    "ML-powered underwriting can reduce premium uncertainty by 20–35%. In Uzbekistan, the motor insurance "
    "sector grew at 18% CAGR between 2020 and 2024, yet fewer than 10% of local insurers use data-driven "
    "risk models (Uzbekistan Insurance Market Report, 2024). Traditional underwriting suffers from four "
    "problems: a narrow feature space missing behavioural signals; human inconsistency; no actionable "
    "feedback to policyholders; and lack of algorithmic transparency, which draws scrutiny under GDPR "
    "Article 22 and the EU AI Act (2024). RiskGuard AI was built to address all four."
)
para(
    "The project aim is to design, develop and evaluate a full-stack ML web application that automates "
    "driver risk profiling, generates explainable risk scores and premium multipliers, and provides "
    "personalised improvement recommendations. Three research questions (RQs) guided the work: "
    "(RQ1) Can ML classifiers outperform statistical baselines for driver risk prediction? "
    "(RQ2) Which features carry the greatest predictive importance? "
    "(RQ3) How can risk scores be presented in an explainable, actionable way for non-technical users?"
)
pb()

# ════════════════════════════════════════════════════════════
# 2. LITERATURE REVIEW  (~140 words)
# ════════════════════════════════════════════════════════════
heading("2. Literature Review")
para(
    "This project is grounded in Design Science Research (DSR) by Hevner et al. (2004) and Peffers et al. "
    "(2007), which treats the creation and evaluation of IT artefacts as legitimate academic research. "
    "RiskGuard AI is the artefact, built to solve the problem of opaque, inconsistent insurance risk "
    "assessment. The Bias–Variance Trade-off (Geman et al., 1992) justifies choosing ensemble methods, "
    "which capture non-linear interactions while controlling overfitting."
)
para(
    "Guelman (2012) demonstrated that Gradient Boosting outperforms Logistic Regression in insurance loss "
    "modelling. Verbelen, Antonio and Claeskens (2018) confirmed this with real Belgian motor data. "
    "Meng et al. (2022) showed that XGBoost and LightGBM consistently outperform linear baselines on large "
    "insurance portfolios. Jiang et al. (2020) found prior accident history is the strongest single "
    "predictor of future claims. GDPR Article 22 and the EU AI Act (2024) make algorithmic explainability "
    "a legal requirement for automated insurance decisions — directly motivating this project's "
    "three-level explainability design."
)
pb()

# ════════════════════════════════════════════════════════════
# 3. METHODOLOGY  (~140 words)
# ════════════════════════════════════════════════════════════
heading("3. Methodology")
para(
    "A pragmatist philosophy (Saunders, Lewis and Thornhill, 2023) was adopted, with methods chosen based "
    "on research questions. The overall strategy follows Peffers et al.'s (2007) six-step DSR process: "
    "problem identification, objectives, design and development, demonstration, evaluation, and "
    "communication. A mixed-methods approach uses quantitative ML evaluation (RQ1 and RQ2) and qualitative "
    "system design analysis (RQ3). Agile/Scrum methodology was adopted with two-week sprints "
    "(Schwaber and Sutherland, 2020) over a ten-week timeline across five sprints covering data generation, "
    "Flask backend, security hardening, frontend and chatbot, and testing and documentation."
)
para(
    "A synthetic dataset of 30,000 driver records was generated using domain-weighted heuristics validated "
    "against five actuarial sources. The dataset contains 18 features (12 input plus 6 engineered). Class "
    "distribution — Low: 35%, Medium: 35%, High: 20%, Very High: 10% — mirrors industry statistics. "
    "An 80/20 stratified train-test split (24,000/6,000 records) was used for all experiments."
)
pb()

# ════════════════════════════════════════════════════════════
# 4. SYSTEM IMPLEMENTATION  (~160 words)
# ════════════════════════════════════════════════════════════
heading("4. System Implementation")
para(
    "RiskGuard AI is a full-stack Flask web application with eleven functional modules: risk assessment, "
    "analytics dashboard, assessment history, driver comparison, AI chatbot, insurance quote calculator, "
    "PDF report generation, batch CSV upload, interactive risk simulator, ML model report, and REST API "
    "documentation. The technology stack is: Python 3.13 and Flask 3.0 for the backend; XGBoost, "
    "scikit-learn, pandas and numpy for the ML pipeline; Bootstrap 5.3 and Chart.js for the frontend; "
    "SQLite with SQLAlchemy ORM for persistence; and Anthropic Claude Sonnet with regex fallback for the "
    "AI chatbot."
)
para(
    "The assessment workflow: a user submits twelve driver and vehicle features; the XGBoost pipeline "
    "predicts a risk category and a continuous score (0–100); a factor contribution engine decomposes the "
    "score into per-feature shares; and an improvement roadmap presents the top three actions with "
    "estimated score savings. Security features include PBKDF2-SHA256 hashing, rate limiting (10/min "
    "login), CSRF tokens, HTTPOnly cookies, and parameterised SQLAlchemy queries."
)
pb()

# ════════════════════════════════════════════════════════════
# 5. RESULTS  (~180 words)
# ════════════════════════════════════════════════════════════
heading("5. Results and Evaluation")

heading("5.1  Model Performance (RQ1)", 2)
tbl = doc.add_table(rows=1, cols=4)
tbl.style = 'Table Grid'
tbl_hdr(tbl, ["Algorithm", "Accuracy", "F1-Score", "ROC-AUC"])
for row in [
    ("Decision Tree", "73.1%", "72.8%", "0.891"),
    ("Logistic Regression", "77.7%", "77.2%", "0.921"),
    ("Random Forest", "81.0%", "80.7%", "0.953"),
    ("Gradient Boosting", "85.0%", "84.8%", "0.970"),
    ("XGBoost (Tuned) ★", "85.22%", "85.1%", "0.9738"),
]:
    tbl_row(tbl, row)
doc.add_paragraph()
para(
    "The tuned XGBoost model achieves 85.22% accuracy and ROC-AUC of 0.9738, exceeding the 85% project "
    "target and outperforming Logistic Regression by 7.5 percentage points (RQ1 answered). In a "
    "10,000-policyholder portfolio this translates to approximately 750 fewer misclassified drivers."
)

heading("5.2  Feature Importance (RQ2)", 2)
para(
    "Previous accidents (24.8%) and driving experience (17.8%) together account for 42.6% of predictive "
    "importance. The top four behavioural features account for 68.6% of predictive power. Gender (0.6%) "
    "and marital status (1.1%) rank lowest — supporting their removal for GDPR and EU AI Act compliance "
    "(RQ2 answered)."
)

heading("5.3  Explainability Design (RQ3)", 2)
para(
    "The three-level explainability design answers RQ3: (1) an animated gauge (0–100) for quick executive "
    "decisions; (2) a per-factor contribution breakdown satisfying GDPR Article 22 requirements; "
    "(3) an improvement roadmap with quantified score savings for policyholders and underwriters."
)
pb()

# ════════════════════════════════════════════════════════════
# 6. DISCUSSION  (~120 words)
# ════════════════════════════════════════════════════════════
heading("6. Discussion")
para(
    "All three research questions are answered positively. The 85.22% XGBoost accuracy confirms that "
    "gradient-boosted tree ensembles substantially outperform linear baselines for motor insurance risk "
    "classification — replicating and extending Guelman (2012) and Verbelen et al. (2018) in a full-stack "
    "production context. Behavioural features dominate demographics, aligning with Jiang et al. (2020) "
    "and supporting the regulatory removal of gender and marital status."
)
para(
    "Three key limitations constrain external validity: (1) synthetic data — the model may perform "
    "differently on real claims data; (2) single-admin architecture — production requires multi-tenant "
    "role-based access control; (3) rule-based explainability — SHAP would provide greater regulatory "
    "standing under the EU AI Act (2024). These limitations define the future work roadmap."
)
pb()

# ════════════════════════════════════════════════════════════
# 7. CONCLUSION  (~100 words)
# ════════════════════════════════════════════════════════════
heading("7. Conclusion")
para(
    "This project successfully designed, developed and evaluated a full-stack ML motor insurance risk "
    "assessment system within ten weeks. The tuned XGBoost model achieves 85.22% accuracy and "
    "ROC-AUC 0.9738, meeting all eight project objectives. The broader finding is that the technical "
    "barriers to ML-powered insurance underwriting are lower than many insurers believe — a single "
    "developer using open-source tools can build a system more accurate and transparent than manual "
    "underwriting. The complete source code is publicly available at: " + GITHUB + ". RiskGuard AI "
    "demonstrates a replicable blueprint for insurance modernisation in emerging markets."
)

heading("8. Recommendations")
bullet("Integrate real telematics data (GPS, speed, braking) to further reduce premium uncertainty.")
bullet("Implement SHAP explainability to satisfy GDPR Article 22 and EU AI Act (2024) fully.")
bullet("Develop multi-tenant RBAC architecture for enterprise deployment.")
bullet("Migrate to PostgreSQL and add automated pytest/CI-CD pipeline.")
bullet("Evaluate LightGBM for production-scale portfolios (100,000+ records).")
pb()

# ════════════════════════════════════════════════════════════
# REFERENCES
# ════════════════════════════════════════════════════════════
heading("References")
refs = [
    "ABI (2023) Motor Insurance Premium Tracker — Full Year 2023. London: Association of British Insurers.",
    "European Parliament (2016) General Data Protection Regulation (EU) 2016/679. Brussels: Official Journal of the EU.",
    "European Parliament (2024) Artificial Intelligence Act (EU) 2024/1689. Brussels: Official Journal of the EU.",
    "Geman, S., Bienenstock, E. and Doursat, R. (1992) 'Neural networks and the bias/variance dilemma', Neural Computation, 4(1), pp.1–58.",
    "Guelman, L. (2012) 'Gradient boosting trees for auto insurance loss cost modeling', Expert Systems with Applications, 39(3), pp.3659–3667.",
    "Hevner, A.R. et al. (2004) 'Design science in information systems research', MIS Quarterly, 28(1), pp.75–105.",
    "Jiang, P. et al. (2020) 'A comprehensive review of ML approaches for predicting road accident risks', Transportation Research Part C, 118, p.102760.",
    "McKinsey and Company (2023) Global Insurance Report 2023. New York: McKinsey.",
    "Meng, S., Shi, P. and Luo, Y. (2022) 'Machine learning methods in insurance', Variance, 15(2).",
    "Peffers, K. et al. (2007) 'A design science research methodology for IS research', JMIS, 24(3), pp.45–77.",
    "Saunders, M., Lewis, P. and Thornhill, A. (2023) Research Methods for Business Students. 9th edn. Harlow: Pearson.",
    "Schwaber, K. and Sutherland, J. (2020) The Scrum Guide. Available at: https://scrumguides.org.",
    "Uzbekistan Insurance Market Report (2024) Insurance Sector 2020–2024. Tashkent: Ministry of Finance.",
    "Verbelen, R., Antonio, K. and Claeskens, G. (2018) 'Unravelling the predictive power of telematics data', JRSS Series A, 181(4), pp.1055–1080.",
]
for ref in refs:
    p = doc.add_paragraph(ref, style='List Bullet')
    if p.runs:
        p.runs[0].font.size = Pt(10)
    p.paragraph_format.space_after = Pt(3)

# ─── Save and count ──────────────────────────────────────────────────────────
doc.save(OUTPUT)
full_text = " ".join([pp.text for pp in doc.paragraphs])
wc = len(re.findall(r'\b\w+\b', full_text))
print(f"Saved: {OUTPUT}")
print(f"Paragraph word count: {wc:,}  (target ~1400)")
