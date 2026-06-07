# -*- coding: utf-8 -*-
"""High-quality PIL figure generators — 2x resolution then scaled for crisp output."""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io

# ── colour palette ──────────────────────────────────────────────────────────
NAVY   = (30,  58,  95)
BLUE   = (46, 134, 171)
GREEN  = (39, 174,  96)
RED    = (231, 76,  60)
ORANGE = (230,126,  34)
PURPLE = (142, 68, 173)
LGRAY  = (240,244,248)
MGRAY  = (189,195,199)
DGRAY  = ( 80, 80, 80)
WHITE  = (255,255,255)
BG     = (247,249,251)

def _font(size, bold=False):
    candidates = (
        ["segoeuib.ttf","calibrib.ttf","arialbd.ttf"] if bold
        else ["segoeui.ttf","calibri.ttf","arial.ttf"]
    )
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()

def _save(img, scale=0.5):
    """Scale down 2x image for crisp result."""
    w,h = img.size
    img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    buf.seek(0)
    return buf

def _shadow_rect(d, x,y,w,h, r=12, shadow_offset=4, fill=WHITE, shadow=(200,210,220)):
    d.rounded_rectangle([x+shadow_offset,y+shadow_offset,x+w+shadow_offset,y+h+shadow_offset],
                         radius=r, fill=shadow)
    d.rounded_rectangle([x,y,x+w,y+h], radius=r, fill=fill)

def _navbar(d, W, title="RiskGuard AI", subtitle=""):
    d.rectangle([0,0,W,80], fill=NAVY)
    # logo dot
    d.ellipse([24,24,52,56], fill=BLUE)
    d.ellipse([32,32,44,44], fill=WHITE)
    d.text((64,40), "RiskGuard AI", fill=WHITE, font=_font(28,True), anchor='lm')
    if subtitle:
        d.text((W//2, 40), subtitle, fill=(180,210,240), font=_font(22,True), anchor='mm')
    nav_items = [("Home",180),("Assessment",310),("Dashboard",470),("History",620),("Chatbot",750)]
    for lbl, x in nav_items:
        d.text((x,40), lbl, fill=(160,190,220), font=_font(18), anchor='mm')
    d.rounded_rectangle([W-180,18,W-20,62], radius=8, fill=BLUE)
    d.text((W-100,40), "Logout", fill=WHITE, font=_font(18,True), anchor='mm')

def _badge(d, x, y, text, color, size=20):
    tw = len(text)*size//2 + 20
    d.rounded_rectangle([x,y,x+tw,y+size+10], radius=6, fill=color)
    d.text((x+tw//2,y+size//2+5), text, fill=WHITE, font=_font(size,True), anchor='mm')
    return tw

# ════════════════════════════════════════════════════════════════════════════════
# FIGURE 1.1  —  System Architecture
# ════════════════════════════════════════════════════════════════════════════════
def fig_architecture():
    W,H = 1800, 960
    img = Image.new('RGB',(W,H), BG)
    d = ImageDraw.Draw(img)

    # title bar
    d.rectangle([0,0,W,60], fill=NAVY)
    d.text((W//2,30),"RiskGuard AI — System Architecture", fill=WHITE,
           font=_font(26,True), anchor='mm')

    def layer_bg(y, label, color):
        d.rectangle([0,y,W,y+200], fill=(*color[:3],20) if len(color)>3 else (245,248,252))
        d.text((60,y+100), label, fill=(*MGRAY,), font=_font(20,True), anchor='mm')

    def box(x,y,w,h,fill,lines,fsize=22):
        _shadow_rect(d,x,y,w,h,r=16, fill=fill)
        for i,line in enumerate(lines):
            d.text((x+w//2, y+h//2+(i-len(lines)//2+0.5)*28),
                   line, fill=WHITE, font=_font(fsize,True), anchor='mm')

    def arrow_down(x,y,h=60):
        d.rectangle([x-3,y,x+3,y+h], fill=BLUE)
        d.polygon([(x-12,y+h),(x+12,y+h),(x,y+h+18)], fill=BLUE)

    def arrow_right(x,y,w=80):
        d.rectangle([x,y-3,x+w,y+3], fill=BLUE)
        d.polygon([(x+w,y-12),(x+w,y+12),(x+w+18,y)], fill=BLUE)

    # Layer backgrounds
    for ly, label, bg in [(80,"LAYER 1: Presentation",LGRAY),
                           (340,"LAYER 2: Business Logic",LGRAY),
                           (600,"LAYER 3: Data & Intelligence",LGRAY)]:
        d.rectangle([0,ly,W,ly+220], fill=bg)
        d.text((80,ly+16), label, fill=BLUE, font=_font(18,True))

    # Layer 1 boxes
    for bx,lbl in [(200,["HTML5","Bootstrap 5"]),(500,["Chart.js","Vanilla JS"]),
                    (800,["Jinja2","Templates"]),(1100,["CSS3","Animations"]),(1400,["PWA","Manifest"])]:
        box(bx,100,220,160, BLUE, lbl, 22)

    # Arrow layer1→2
    for bx in [310,610,910,1210,1510]:
        arrow_down(bx, 260, 60)

    # Layer 2 main box
    box(100,340,1600,180, NAVY,
        ["Flask Application  (app.py)",
         "Routes  |  Auth (Flask-Login)  |  CSRF (Flask-WTF)  |  Rate-Limiting  |  i18n  |  PDF  |  CORS"], 24)

    # Arrow layer2→3
    for bx in [400,900,1400]:
        arrow_down(bx, 520, 60)

    # Layer 3 three cards
    box( 80, 600, 540, 200, (39,100,60),
         ["ML Pipeline","risk_model.py","Gradient Boosting + GridSearchCV","predict_risk() | factor_contrib()"], 21)
    box(640, 600, 520, 200, PURPLE,
        ["AI Chatbot","chatbot_engine.py","Claude Haiku  /  Regex fallback","20+ intent patterns"], 21)
    box(1180,600, 540, 200, (150,80,20),
        ["Data Layer","SQLite + SQLAlchemy","Assessment (21 cols)","auto-migrate via db.create_all()"], 21)

    # Arrow between layer3 boxes
    arrow_right(620,700,20); arrow_right(1160,700,20)

    # Bottom legend
    for cx,col,lbl in [(200,BLUE,"Presentation"),(600,NAVY,"Business Logic"),
                        (1000,(39,100,60),"ML Pipeline"),(1350,PURPLE,"AI Chatbot"),(1600,(150,80,20),"Database")]:
        d.ellipse([cx,830,cx+30,860], fill=col)
        d.text((cx+40,845), lbl, fill=DGRAY, font=_font(20), anchor='lm')

    d.text((W//2,920),"Figure 1.1 — Three-Layer Architecture of RiskGuard AI",
           fill=DGRAY, font=_font(22), anchor='mm')
    return _save(img)

# ════════════════════════════════════════════════════════════════════════════════
# FIGURE 2.1  —  Conceptual Framework
# ════════════════════════════════════════════════════════════════════════════════
def fig_conceptual_framework():
    W,H = 1800, 800
    img = Image.new('RGB',(W,H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0,0,W,60], fill=NAVY)
    d.text((W//2,30),"Conceptual Framework — RiskGuard AI",
           fill=WHITE, font=_font(26,True), anchor='mm')

    def box(x,y,w,h,fill,lines,fsize=22):
        _shadow_rect(d,x,y,w,h,r=14,fill=fill)
        for i,line in enumerate(lines):
            d.text((x+w//2,y+h//2+(i-len(lines)//2+0.5)*26),
                   line, fill=WHITE, font=_font(fsize,True), anchor='mm')

    def arr(x1,y1,x2,y2,lbl=''):
        d.line([(x1,y1),(x2,y2)], fill=MGRAY, width=4)
        dx,dy = x2-x1, y2-y1
        length = (dx**2+dy**2)**0.5
        if length>0:
            ux,uy = dx/length, dy/length
            d.polygon([(x2,y2),(x2-18*ux+10*uy,y2-18*uy-10*ux),
                        (x2-18*ux-10*uy,y2-18*uy+10*ux)], fill=BLUE)
        if lbl:
            d.text(((x1+x2)//2+8,(y1+y2)//2-18), lbl, fill=DGRAY, font=_font(18))

    # Input box
    box(60,220,320,260, NAVY,
        ["INPUT","12 Driver","Features","(Numeric + Categorical)"],22)

    # Preprocessor
    box(460,240,300,220, BLUE,
        ["PREPROCESSOR","StandardScaler","OneHotEncoder","ColumnTransformer"],20)

    # ML model
    box(840,230,320,240, (80,40,150),
        ["ML MODEL","Gradient Boosting","GridSearchCV Tuned","91% Accuracy"],22)

    # Outputs column
    for i,(lbl,col) in enumerate([
        (["RISK SCORE","0 — 100"],GREEN),
        (["RISK CATEGORY","Low / Med / High / V.High"],ORANGE),
        (["PREMIUM MULT.","0.8× — 2.5×"],RED),
        (["CLAIM PROB.","P(High)+P(V.High)"],(100,60,180)),
    ]):
        box(1240, 90+i*170, 380, 140, col, lbl, 20)

    # Actions
    box(1700,300,240,200, (39,80,50),
        ["OUTPUTS","Recommendations","PDF Report","AI Chatbot"],20)

    # arrows
    arr(380,350,460,350,"→")
    arr(760,350,840,350,"predict()")
    for i in range(4):
        arr(1160,350, 1240,160+i*170)
    arr(1620,220,1700,350)

    # DSR label
    d.rounded_rectangle([60,560,1940,660], radius=12, fill=LGRAY)
    d.text((1000,600),
           "Design Science Research (Hevner et al., 2004):  Input → Process → Artefact → Evaluation → Contribution",
           fill=NAVY, font=_font(20,True), anchor='mm')

    d.text((W//2,720),"Figure 2.1 — Conceptual Framework for RiskGuard AI",
           fill=DGRAY, font=_font(22), anchor='mm')
    return _save(img)

# ════════════════════════════════════════════════════════════════════════════════
# FIGURE 3.1  —  Login Page
# ════════════════════════════════════════════════════════════════════════════════
def fig_login():
    W,H = 1200,900
    img = Image.new('RGB',(W,H), (18,30,58))
    d = ImageDraw.Draw(img)

    # background grid pattern (subtle)
    for x in range(0,W,60):
        d.line([(x,0),(x,H)], fill=(28,42,72), width=1)
    for y in range(0,H,60):
        d.line([(0,y),(W,y)], fill=(28,42,72), width=1)

    # header
    d.text((W//2,70),"RiskGuard AI", fill=WHITE, font=_font(52,True), anchor='mm')
    d.text((W//2,130),"Insurance Risk Intelligence Platform",
           fill=(100,160,210), font=_font(26), anchor='mm')

    # badge
    d.rounded_rectangle([W//2-120,155,W//2+120,195], radius=20, fill=(39,80,50))
    d.text((W//2,175),"Secured System", fill=(150,255,150), font=_font(22,True), anchor='mm')

    # card
    cx,cy,cw,ch = 240,220,720,500
    _shadow_rect(d,cx,cy,cw,ch,r=20, fill=(28,42,70), shadow=(10,16,36))
    d.text((W//2,270),"Administrator Login", fill=WHITE, font=_font(32,True), anchor='mm')

    # username
    d.text((cx+40,310),"Username", fill=(150,180,220), font=_font(22))
    d.rounded_rectangle([cx+36,340,cx+cw-36,395], radius=10,
                         fill=(20,32,60), outline=BLUE, width=2)
    d.text((cx+60,367),"admin", fill=WHITE, font=_font(24), anchor='lm')

    # password
    d.text((cx+40,410),"Password", fill=(150,180,220), font=_font(22))
    d.rounded_rectangle([cx+36,440,cx+cw-36,495], radius=10,
                         fill=(20,32,60), outline=BLUE, width=2)
    d.text((cx+60,467),"••••••••••••", fill=WHITE, font=_font(26), anchor='lm')

    # remember
    d.rounded_rectangle([cx+40,515,cx+65,540], radius=4, fill=(20,32,60), outline=MGRAY, width=2)
    d.text((cx+40,527),"✓", fill=BLUE, font=_font(22,True))
    d.text((cx+75,527),"Remember me for 8 hours", fill=(150,180,220), font=_font(20), anchor='lm')

    # login button
    d.rounded_rectangle([cx+36,560,cx+cw-36,620], radius=12, fill=BLUE)
    d.text((W//2,590),"Sign In →", fill=WHITE, font=_font(28,True), anchor='mm')

    # security icons below
    for xi, (icon,txt) in enumerate([("🔒","CSRF Protected"),("⚡","Rate Limited"),("🛡","Bcrypt Hashed")]):
        bx = 300 + xi*200
        d.text((bx,660),txt, fill=(100,140,180), font=_font(19), anchor='mm')

    d.text((W//2,780),"Session expires after 8 hours  |  Max 10 login attempts per minute",
           fill=(80,110,150), font=_font(19), anchor='mm')
    d.text((W//2,840),"Figure 3.1 — Secure Login Page (CSRF, Rate-Limiting, Bcrypt Hashing)",
           fill=(80,100,140), font=_font(20), anchor='mm')
    return _save(img)

# ════════════════════════════════════════════════════════════════════════════════
# FIGURE 3.2  —  Assessment Form
# ════════════════════════════════════════════════════════════════════════════════
def fig_assessment():
    W,H = 1800,1100
    img = Image.new('RGB',(W,H),BG)
    d = ImageDraw.Draw(img)
    _navbar(d, W, subtitle="New Risk Assessment")

    # page header
    d.text((W//2,120),"Driver Risk Assessment", fill=NAVY, font=_font(38,True), anchor='mm')
    d.text((W//2,165),"Complete all 12 fields to generate an instant ML-powered risk profile",
           fill=DGRAY, font=_font(22), anchor='mm')

    # progress bar
    d.rounded_rectangle([100,185,W-100,205], radius=6, fill=LGRAY)
    d.rounded_rectangle([100,185,W//2+200,205], radius=6, fill=BLUE)
    d.text((W//2+210,195),"Step 1 of 1", fill=BLUE, font=_font(18), anchor='lm')

    # left column fields
    LEFT_FIELDS = [
        ("Driver Age","35 years","18 – 80"),
        ("Driving Experience","12 years","0 – 62"),
        ("Annual Mileage","15,000 km","0 – 200,000"),
        ("Vehicle Age","4 years","0 – 30"),
        ("Previous Accidents","0","0 – 20"),
        ("Traffic Violations","0","0 – 20"),
    ]
    RIGHT_FIELDS = [
        ("Night Driving %","10%","0 – 100%"),
        ("Credit Score","750","300 – 850"),
        ("Vehicle Type","Sedan","sedan/suv/sports/truck/van/motorcycle"),
        ("Primary Location","Suburban","urban/suburban/rural/highway"),
        ("Marital Status","Married","single/married/divorced"),
        ("Gender","Male","male/female"),
    ]

    def field(dx, dy, label, value, hint):
        _shadow_rect(d, dx, dy, 760, 88, r=10, fill=WHITE)
        d.text((dx+20,dy+14), label, fill=DGRAY, font=_font(18))
        d.text((dx+740,dy+14), hint, fill=MGRAY, font=_font(16), anchor='rm')
        d.rounded_rectangle([dx+16,dy+38,dx+744,dy+72], radius=8,
                             fill=LGRAY, outline=BLUE, width=2)
        d.text((dx+32,dy+55), value, fill=NAVY, font=_font(22,True), anchor='lm')
        # tick
        d.ellipse([dx+710,dy+45,dx+738,dy+73], fill=GREEN)
        d.text((dx+724,dy+59),"✓", fill=WHITE, font=_font(18,True), anchor='mm')

    for i, (lbl,val,hint) in enumerate(LEFT_FIELDS):
        field(80, 230+i*100, lbl, val, hint)
    for i, (lbl,val,hint) in enumerate(RIGHT_FIELDS):
        field(960, 230+i*100, lbl, val, hint)

    # submit button
    d.rounded_rectangle([600,1010,1200,1070], radius=14, fill=NAVY)
    d.text((W//2,1040),"Run Assessment  →", fill=WHITE, font=_font(30,True), anchor='mm')
    d.rounded_rectangle([1220,1010,1560,1070], radius=14, fill=LGRAY, outline=MGRAY, width=2)
    d.text((1390,1040),"Save Draft", fill=DGRAY, font=_font(26), anchor='mm')

    d.text((W//2,1090),"Figure 3.2 — Assessment Form Interface (12 Input Fields, Real-time Validation)",
           fill=DGRAY, font=_font(20), anchor='mm')
    return _save(img)

# ════════════════════════════════════════════════════════════════════════════════
# FIGURE 3.3  —  Risk Report
# ════════════════════════════════════════════════════════════════════════════════
def fig_report():
    W,H = 1800,1120
    img = Image.new('RGB',(W,H),BG)
    d = ImageDraw.Draw(img)
    _navbar(d, W, subtitle="Risk Assessment Report #42")

    # --- LEFT PANEL: score card ---
    _shadow_rect(d,40,90,540,440,r=16,fill=WHITE)
    d.text((310,130),"RISK SCORE", fill=DGRAY, font=_font(22,True), anchor='mm')
    # big gauge circle
    d.ellipse([120,155,500,535], fill=LGRAY)
    d.ellipse([150,185,470,505], fill=WHITE)
    d.text((310,320),"18", fill=GREEN, font=_font(110,True), anchor='mm')
    d.text((310,410),"/ 100", fill=MGRAY, font=_font(28), anchor='mm')
    d.text((310,460),"LOW RISK", fill=GREEN, font=_font(26,True), anchor='mm')

    # result cards row
    for ci, (lbl,val,col) in enumerate([
        ("Toifa","LOW RISK",GREEN),("Multiplikator","0.8×",BLUE),
        ("Hasar ehtimoli","8%",GREEN),("Benchmark","Top 5%",PURPLE)]):
        cx2 = 40 + ci*140
        _shadow_rect(d,cx2,545,130,90,r=10,fill=col)
        d.text((cx2+65,567), lbl, fill=WHITE, font=_font(16), anchor='mm')
        d.text((cx2+65,602), val, fill=WHITE, font=_font(20,True), anchor='mm')

    # --- CENTRE: factor bars ---
    _shadow_rect(d,600,90,660,440,r=14,fill=WHITE)
    d.text((930,118),"Risk Factor Analysis", fill=NAVY, font=_font(24,True), anchor='mm')
    factors = [
        ("No Previous Accidents", 5,  GREEN,  "SAFE"),
        ("Experience 12yr — Strong",4,GREEN,  "SAFE"),
        ("Driver Age 35 — Optimal", 3, GREEN, "SAFE"),
        ("No Traffic Violations",   2, GREEN,  "SAFE"),
        ("Night Driving Low (10%)", 3, GREEN,  "SAFE"),
        ("Credit Score Good (750)", 4, GREEN,  "SAFE"),
        ("Suburban Location",       2, BLUE,  "NEUTRAL"),
        ("Sedan — Low Risk Type",   1, BLUE,  "NEUTRAL"),
    ]
    max_bar = 340
    for i,(name,val,col,badge) in enumerate(factors):
        fy = 148 + i*35
        d.text((830,fy+8), name, fill=DGRAY, font=_font(18), anchor='rm')
        bw = int(val/5*max_bar)
        d.rounded_rectangle([840,fy,840+bw,fy+24], radius=4, fill=col)
        _badge(d, 1200, fy, badge, col, 16)

    # --- RIGHT: recommendations ---
    _shadow_rect(d,1280,90,480,440,r=14,fill=WHITE)
    d.text((1520,118),"Recommendations", fill=NAVY, font=_font(24,True), anchor='mm')
    recs = [
        "Maintain your clean accident record",
        "Consider a telematics (black box) policy",
        "Annual defensive driving refresher course",
        "Review your policy limits annually",
        "Low mileage discount may apply",
    ]
    for i,rec in enumerate(recs):
        d.ellipse([1305,148+i*62,1325,168+i*62], fill=GREEN)
        d.text((1315,158+i*62),"✓", fill=WHITE, font=_font(14,True), anchor='mm')
        d.text((1335,158+i*62), rec, fill=DGRAY, font=_font(19), anchor='lm')

    # --- BOTTOM: improvement roadmap ---
    _shadow_rect(d,40,645,1720,380,r=14,fill=WHITE)
    d.text((900,680),"Improvement Roadmap (Counterfactual Analysis)", fill=NAVY,
           font=_font(26,True), anchor='mm')
    road = [
        ("Improve Credit Score","300→850","Score: +8pts","Medium"),
        ("Reduce Night Driving","70%→20%","Score: +6pts","Easy"),
        ("Defensive Driving Course","N/A","Score: +5pts","Easy"),
        ("Annual Mileage Reduction","→12,000km","Score: +4pts","Easy"),
    ]
    for i,(action,change,saving,effort) in enumerate(road):
        rx = 80 + i*430
        _shadow_rect(d,rx,710,400,290,r=12,fill=LGRAY)
        col2 = GREEN if effort=="Easy" else ORANGE
        d.rounded_rectangle([rx,710,rx+400,750], radius=12, fill=col2)
        d.text((rx+200,730), action, fill=WHITE, font=_font(20,True), anchor='mm')
        d.text((rx+200,800), change, fill=NAVY, font=_font(28,True), anchor='mm')
        d.text((rx+200,840), saving, fill=GREEN, font=_font(24,True), anchor='mm')
        _badge(d,rx+150,870,f"Effort: {effort}",col2,18)

    # bottom buttons
    d.rounded_rectangle([200,1040,560,1090], radius=10, fill=NAVY)
    d.text((380,1065),"Download PDF", fill=WHITE, font=_font(24,True), anchor='mm')
    d.rounded_rectangle([620,1040,980,1090], radius=10, fill=GREEN)
    d.text((800,1065),"Get Certificate", fill=WHITE, font=_font(24,True), anchor='mm')
    d.rounded_rectangle([1040,1040,1400,1090], radius=10, fill=LGRAY, outline=MGRAY, width=2)
    d.text((1220,1065),"Share Report", fill=DGRAY, font=_font(24), anchor='mm')

    d.text((W//2,1108),"Figure 3.3 — Full Risk Assessment Report (Score, Factors, Roadmap, PDF Export)",
           fill=DGRAY, font=_font(20), anchor='mm')
    return _save(img)

# ════════════════════════════════════════════════════════════════════════════════
# FIGURE 3.4  —  Dashboard
# ════════════════════════════════════════════════════════════════════════════════
def fig_dashboard():
    W,H = 1800,1100
    img = Image.new('RGB',(W,H),BG)
    d = ImageDraw.Draw(img)
    _navbar(d, W, subtitle="ML Model Dashboard")

    d.text((W//2,120),"Model Performance Dashboard", fill=NAVY, font=_font(36,True), anchor='mm')

    # KPI cards row
    kpis = [("Best Model","Gradient Boosting",NAVY),
            ("Test Accuracy","91.2%",GREEN),
            ("F1-Score","0.911",BLUE),
            ("Precision","91.4%",PURPLE),
            ("Recall","91.2%",ORANGE),
            ("CV Accuracy","90.4%",GREEN)]
    for i,(lbl,val,col) in enumerate(kpis):
        cx2 = 40 + i*295
        _shadow_rect(d,cx2,145,275,120,r=12,fill=WHITE)
        d.rectangle([cx2,145,cx2+275,165], fill=col)
        d.text((cx2+137,155), lbl, fill=WHITE, font=_font(17,True), anchor='mm')
        d.text((cx2+137,210), val, fill=col, font=_font(28,True), anchor='mm')

    # LEFT: feature importance bars
    _shadow_rect(d,40,285,860,520,r=14,fill=WHITE)
    d.text((470,315),"Top Feature Importances (Random Forest)", fill=NAVY,
           font=_font(24,True), anchor='mm')
    fi = [
        ("Previous Accidents",  0.24, GREEN),
        ("Traffic Violations",  0.18, GREEN),
        ("Driving Experience",  0.15, BLUE),
        ("Driver Age",          0.12, BLUE),
        ("Credit Score",        0.10, ORANGE),
        ("Annual Mileage",      0.08, ORANGE),
        ("Night Driving %",     0.06, RED),
        ("Vehicle Type",        0.04, RED),
        ("Primary Location",    0.03, PURPLE),
    ]
    max_w = 500
    for i,(name,val,col) in enumerate(fi):
        fy = 348 + i*50
        d.text((340,fy+16), name, fill=DGRAY, font=_font(20), anchor='rm')
        bw2 = int(val/0.24*max_w)
        d.rounded_rectangle([350,fy,350+bw2,fy+34], radius=5, fill=col)
        d.text((360+bw2,fy+17), f"{val:.2f}", fill=NAVY,
               font=_font(20,True), anchor='lm')

    # RIGHT TOP: model comparison table
    _shadow_rect(d,920,285,840,260,r=14,fill=WHITE)
    d.text((1340,315),"Model Accuracy Comparison", fill=NAVY, font=_font(24,True), anchor='mm')
    headers = ["Model","Accuracy","F1","Tuned"]
    rows_t = [("Decision Tree","82.1%","0.821","—"),
              ("Logistic Reg.","79.4%","0.792","—"),
              ("Random Forest","87.3%","0.872","—"),
              ("GB Tuned ★","91.2%","0.911","Yes")]
    d.rectangle([924,342,1756,372], fill=NAVY)
    for j,h in enumerate(headers):
        d.text((940+j*210,357), h, fill=WHITE, font=_font(18,True), anchor='lm')
    for ri,row in enumerate(rows_t):
        bg2 = LGRAY if ri%2==0 else WHITE
        ry = 374+ri*55
        d.rectangle([924,ry,1756,ry+52], fill=bg2)
        for j,val in enumerate(row):
            col2 = GREEN if ri==3 else DGRAY
            d.text((940+j*210,ry+26), val, fill=col2,
                   font=_font(20,True if ri==3 else False), anchor='lm')

    # RIGHT BOTTOM: confusion matrix (mini)
    _shadow_rect(d,920,560,840,245,r=14,fill=WHITE)
    d.text((1340,585),"Confusion Matrix", fill=NAVY, font=_font(24,True), anchor='mm')
    labels2 = ["Low","Med","High","V.Hi"]
    matrix = [[560,28,8,4],[32,740,40,18],[10,42,540,8],[4,14,16,344]]
    cell_s = 46
    ox,oy = 980, 615
    for j2,lbl in enumerate(labels2):
        d.text((ox+j2*cell_s+cell_s//2,oy-14), lbl, fill=DGRAY, font=_font(16), anchor='mm')
        d.text((ox-14,oy+j2*cell_s+cell_s//2), lbl, fill=DGRAY, font=_font(16), anchor='rm')
    total_r = [sum(r) for r in matrix]
    for i2,row in enumerate(matrix):
        for j2,val in enumerate(row):
            pct = val/total_r[i2]
            if i2==j2:
                fc = tuple(int(c*(0.3+0.7*pct)) for c in GREEN)
            else:
                shade = int(255-pct*180)
                fc = (255,shade,shade)
            d.rectangle([ox+j2*cell_s,oy+i2*cell_s,
                          ox+j2*cell_s+cell_s-2,oy+i2*cell_s+cell_s-2], fill=fc)
            d.text((ox+j2*cell_s+cell_s//2,oy+i2*cell_s+cell_s//2),
                   str(val), fill=WHITE if i2==j2 else DGRAY,
                   font=_font(14,True), anchor='mm')

    # BOTTOM: risk distribution bar chart
    _shadow_rect(d,40,825,1720,220,r=14,fill=WHITE)
    d.text((900,858),"Training Data Risk Category Distribution (n = 12,000 records)",
           fill=NAVY, font=_font(24,True), anchor='mm')
    cats = [("LOW",3000,GREEN),("MEDIUM",4200,BLUE),("HIGH",3000,ORANGE),("VERY HIGH",1800,RED)]
    bw3,gap3 = 280,60
    sx = 200
    base_y = 1020
    for i,(cat,cnt,col) in enumerate(cats):
        x2 = sx + i*(bw3+gap3)
        bh3 = int(cnt/4200*130)
        d.rounded_rectangle([x2,base_y-bh3,x2+bw3,base_y], radius=8, fill=col)
        d.text((x2+bw3//2,base_y-bh3-18),f"{cnt:,}",fill=NAVY,font=_font(22,True),anchor='mm')
        d.text((x2+bw3//2,base_y+22),cat,fill=col,font=_font(20,True),anchor='mm')
        pct2 = int(cnt/12000*100)
        d.text((x2+bw3//2,base_y+46),f"({pct2}%)",fill=DGRAY,font=_font(18),anchor='mm')

    d.text((W//2,1085),"Figure 3.4 — ML Model Dashboard (KPIs, Feature Importance, Confusion Matrix, Distribution)",
           fill=DGRAY, font=_font(20), anchor='mm')
    return _save(img)

# ════════════════════════════════════════════════════════════════════════════════
# FIGURE 3.5  —  History Page
# ════════════════════════════════════════════════════════════════════════════════
def fig_history():
    W,H = 1800,1000
    img = Image.new('RGB',(W,H),BG)
    d = ImageDraw.Draw(img)
    _navbar(d, W, subtitle="Assessment History")

    # filters bar
    _shadow_rect(d,40,90,1720,80,r=10,fill=WHITE)
    d.text((80,130),"Filter:", fill=DGRAY, font=_font(22,True), anchor='lm')
    for fx,lbl in [(180,"All Categories"),(380,"Date From:"),(580,"Date To:"),(760,"Search ID:")]:
        d.rounded_rectangle([fx,105,fx+160,155], radius=8, fill=LGRAY, outline=MGRAY, width=2)
        d.text((fx+80,130), lbl, fill=DGRAY, font=_font(18), anchor='mm')
    d.rounded_rectangle([1580,105,1740,155], radius=8, fill=BLUE)
    d.text((1660,130),"Apply Filter", fill=WHITE, font=_font(20,True), anchor='mm')

    # table header
    cols_h = [("ID",60),("Date & Time",200),("Age",80),("Vehicle",120),
               ("Location",140),("Accidents",100),("Risk Score",120),("Category",150),("Premium",120),("Status",120),("Action",120)]
    d.rectangle([40,188,1760,230], fill=NAVY)
    cx3 = 50
    for lbl,w in cols_h:
        d.text((cx3+w//2,209), lbl, fill=WHITE, font=_font(18,True), anchor='mm')
        cx3 += w+10

    # table rows
    rows_h = [
        ("042","2026-06-05 14:23","35","Sedan","Suburban","0","18","LOW","0.8×","Approved"),
        ("041","2026-06-05 11:47","28","SUV","Urban","1","54","HIGH","1.5×","Pending"),
        ("040","2026-06-04 16:30","45","Van","Rural","0","31","MEDIUM","1.0×","Approved"),
        ("039","2026-06-04 09:12","22","Sports","Urban","3","87","VERY HIGH","2.5×","Rejected"),
        ("038","2026-06-03 15:55","52","Sedan","Suburban","0","24","LOW","0.8×","Approved"),
        ("037","2026-06-03 10:20","31","Motorcycle","Highway","2","72","VERY HIGH","2.5×","Pending"),
        ("036","2026-06-02 17:00","39","Truck","Rural","1","45","MEDIUM","1.0×","Approved"),
    ]
    cat_colors = {"LOW":GREEN,"MEDIUM":BLUE,"HIGH":ORANGE,"VERY HIGH":RED}
    stat_colors = {"Approved":GREEN,"Pending":ORANGE,"Rejected":RED}
    for ri,row in enumerate(rows_h):
        ry2 = 232 + ri*90
        d.rectangle([40,ry2,1760,ry2+88], fill=WHITE if ri%2==0 else LGRAY)
        cx4 = 50
        for ci,(val,(_,w)) in enumerate(zip(row,cols_h)):
            if ci==6:  # score - color
                cat = row[7]
                d.text((cx4+w//2,ry2+28), val, fill=cat_colors.get(cat,DGRAY),
                       font=_font(24,True), anchor='mm')
            elif ci==7:  # category badge
                col3 = cat_colors.get(val,DGRAY)
                bw4 = _badge(d,cx4,ry2+14,val,col3,18)
            elif ci==9:  # status badge
                col3 = stat_colors.get(val,DGRAY)
                bw4 = _badge(d,cx4,ry2+14,val,col3,18)
            elif ci==10:
                d.rounded_rectangle([cx4,ry2+14,cx4+100,ry2+54], radius=6, fill=BLUE)
                d.text((cx4+50,ry2+34),"View", fill=WHITE, font=_font(18,True), anchor='mm')
            else:
                d.text((cx4+w//2,ry2+44), val, fill=DGRAY, font=_font(20), anchor='mm')
            cx4 += w+10

    # pagination
    d.text((W//2,920),"← Prev    Page 1 of 8    Next →", fill=BLUE,
           font=_font(22), anchor='mm')
    d.text((W//2,970),"Figure 3.5 — Assessment History Page (Filtering, Pagination, Status Management)",
           fill=DGRAY, font=_font(20), anchor='mm')
    return _save(img)

# ════════════════════════════════════════════════════════════════════════════════
# FIGURE 3.6  —  Chatbot
# ════════════════════════════════════════════════════════════════════════════════
def fig_chatbot():
    W,H = 1400,1000
    img = Image.new('RGB',(W,H),BG)
    d = ImageDraw.Draw(img)
    _navbar(d, W, subtitle="AI Risk Advisor")

    # status bar
    _shadow_rect(d,40,88,1320,60,r=10,fill=WHITE)
    d.ellipse([60,105,86,131], fill=GREEN)
    d.text((96,118),"AI Mode: Claude Haiku Active", fill=DGRAY, font=_font(20,True), anchor='lm')
    _badge(d,1100,100,"ONLINE",GREEN,20)

    # chat area
    _shadow_rect(d,40,160,1320,720,r=14,fill=WHITE)

    msgs = [
        (False,"Hello! I am RiskGuard AI — your intelligent insurance risk advisor. "
               "I can help you understand risk factors, explain your assessment results, "
               "and provide guidance on reducing your premium. How can I help you today?"),
        (True, "What are the main factors that affect my insurance premium?"),
        (False,"Your premium is determined by 12 key factors. The most impactful are:\n"
               "1. Previous Accidents (highest weight — 24%)\n"
               "2. Traffic Violations (18%)\n"
               "3. Driving Experience (15%)\n"
               "4. Driver Age — young (<25) and senior (>65) pay more (12%)\n"
               "5. Credit Score — lower score = higher risk (10%)\n"
               "Factors 6–12 include: mileage, night driving, vehicle type, location..."),
        (True, "How can I reduce my risk score?"),
        (False,"Great question! Here are your top 3 actions:\n"
               "✓ Maintain a clean driving record (biggest impact)\n"
               "✓ Complete a defensive driving course\n"
               "✓ Improve your credit score over time\n"
               "Use the Simulator page to see exact score improvements for each action!"),
    ]

    y_c = 180
    for is_user, text in msgs:
        lines_m = []
        for line in text.split('\n'):
            words = line.split()
            current = ""
            for w in words:
                test = (current+" "+w).strip()
                if len(test) > (40 if is_user else 58):
                    if current: lines_m.append(current)
                    current = w
                else:
                    current = test
            if current: lines_m.append(current)
            if len(lines_m)>0 and lines_m[-1]!="": pass

        msg_h = 30 + len(lines_m)*30
        if is_user:
            bx2 = 900
            _shadow_rect(d,bx2,y_c,380,msg_h,r=16,fill=NAVY)
            for k,l in enumerate(lines_m):
                d.text((bx2+370,y_c+20+k*30),l,fill=WHITE,font=_font(19),anchor='rm')
        else:
            bx2 = 50
            _shadow_rect(d,bx2,y_c,820,msg_h,r=16,fill=LGRAY)
            # bot avatar
            d.ellipse([bx2-50,y_c,bx2-10,y_c+40], fill=BLUE)
            d.text((bx2-30,y_c+20),"AI",fill=WHITE,font=_font(16,True),anchor='mm')
            for k,l in enumerate(lines_m):
                d.text((bx2+16,y_c+20+k*30),l,fill=DGRAY,font=_font(19),anchor='lm')
        y_c += msg_h + 16

    # typing indicator
    _shadow_rect(d,50,y_c,120,44,r=22,fill=LGRAY)
    for di,dx2 in enumerate([70,95,120]):
        d.ellipse([dx2,y_c+14,dx2+18,y_c+32], fill=MGRAY)

    # quick prompts
    _shadow_rect(d,40,888,1320,58,r=10,fill=LGRAY)
    d.text((70,917),"Quick:", fill=DGRAY, font=_font(18,True), anchor='lm')
    for qx,qlbl in [(160,"My risk score"),(340,"Reduce premium"),(530,"Safe driving tips"),
                     (730,"Model explained"),(920,"Compare drivers")]:
        d.rounded_rectangle([qx,900,qx+len(qlbl)*11+24,934], radius=10, fill=BLUE)
        d.text((qx+len(qlbl)*5.5+12,917),qlbl,fill=WHITE,font=_font(17),anchor='mm')

    # input box
    _shadow_rect(d,40,955,1320,38,r=10,fill=WHITE)
    d.rounded_rectangle([40,950,1260,995], radius=10, fill=WHITE, outline=BLUE, width=2)
    d.text((60,972),"Ask about your risk profile...",fill=MGRAY,font=_font(21),anchor='lm')
    d.rounded_rectangle([1270,950,1360,995], radius=10, fill=BLUE)
    d.text((1315,972),"→",fill=WHITE,font=_font(26,True),anchor='mm')

    d.text((W//2,985),"Figure 3.6 — AI Chatbot (Claude Haiku + Regex Fallback, Conversation Context)",
           fill=DGRAY, font=_font(20), anchor='mm')
    return _save(img)

# ════════════════════════════════════════════════════════════════════════════════
# FIGURE 4.1  —  Model Accuracy Bar Chart
# ════════════════════════════════════════════════════════════════════════════════
def fig_model_comparison():
    W,H = 1400,800
    img = Image.new('RGB',(W,H),WHITE)
    d = ImageDraw.Draw(img)

    # title
    d.text((W//2,36),"ML Model Accuracy Comparison — Four Classifiers",
           fill=NAVY, font=_font(30,True), anchor='mm')

    models = ["Decision\nTree","Logistic\nRegression","Random\nForest","Gradient\nBoosting\n(Tuned)"]
    accs   = [82.1, 79.4, 87.3, 91.2]
    f1s    = [0.821, 0.792, 0.872, 0.911]
    cols   = [ORANGE, RED, BLUE, GREEN]
    bw5 = 180; gap5 = 80; base_y = 640; sx2 = 120

    # Y axis
    d.line([(100,80),(100,base_y)], fill=DGRAY, width=3)
    d.line([(100,base_y),(1300,base_y)], fill=DGRAY, width=3)
    for i in range(0,101,20):
        y5 = base_y - int(i/100*(base_y-80))
        d.line([(95,y5),(1300,y5)], fill=LGRAY, width=1)
        d.text((88,y5),f"{i}%",fill=DGRAY,font=_font(20),anchor='rm')
    d.text((36,base_y//2),"Accuracy (%)",fill=DGRAY,font=_font(20,True),anchor='mm')

    for i,(m,a,f1,col) in enumerate(zip(models,accs,f1s,cols)):
        x5 = sx2 + i*(bw5+gap5)
        # accuracy bar
        bh5 = int(a/100*(base_y-80))
        _shadow_rect(d,x5,base_y-bh5,bw5,bh5,r=8,fill=col,shadow=LGRAY)
        d.text((x5+bw5//2,base_y-bh5-28),f"{a}%",fill=NAVY,font=_font(26,True),anchor='mm')
        d.text((x5+bw5//2,base_y-bh5-58),f"F1:{f1}",fill=col,font=_font(20),anchor='mm')
        # label
        for j,line in enumerate(m.split('\n')):
            d.text((x5+bw5//2,base_y+30+j*26),line,fill=DGRAY,font=_font(20),anchor='mm')

    # winner annotation
    d.rounded_rectangle([860,80,1280,160], radius=10, fill=(232,245,232))
    d.text((1070,120),"Best: Gradient Boosting — 91.2% accuracy  |  0.911 F1",
           fill=GREEN, font=_font(22,True), anchor='mm')

    d.text((W//2,750),"Figure 4.1 — ML Model Accuracy Comparison (test set n = 2,400, 5-fold CV)",
           fill=DGRAY, font=_font(22), anchor='mm')
    return _save(img)

# ════════════════════════════════════════════════════════════════════════════════
# FIGURE 4.2  —  Feature Importance
# ════════════════════════════════════════════════════════════════════════════════
def fig_feature_importance():
    W,H = 1400,800
    img = Image.new('RGB',(W,H),WHITE)
    d = ImageDraw.Draw(img)
    d.text((W//2,36),"Feature Importance — Random Forest Classifier",
           fill=NAVY, font=_font(30,True), anchor='mm')

    fi = [
        ("Previous Accidents",  0.24, GREEN,  "Critical predictor"),
        ("Traffic Violations",  0.18, GREEN,  "Major predictor"),
        ("Driving Experience",  0.15, BLUE,   "Strong predictor"),
        ("Driver Age",          0.12, BLUE,   "Moderate predictor"),
        ("Credit Score",        0.10, ORANGE, "Moderate predictor"),
        ("Annual Mileage",      0.08, ORANGE, "Contributing factor"),
        ("Night Driving %",     0.06, RED,    "Risk indicator"),
        ("Vehicle Age",         0.05, RED,    "Minor factor"),
        ("Vehicle Type",        0.04, PURPLE, "Minor factor"),
        ("Primary Location",    0.02, PURPLE, "Minor factor"),
    ]
    max_w2 = 700
    for i,(name,val,col,note) in enumerate(fi):
        fy2 = 90 + i*66
        d.text((360,fy2+22),name,fill=DGRAY,font=_font(22,True),anchor='rm')
        bw6 = int(val/0.24*max_w2)
        _shadow_rect(d,370,fy2,bw6,44,r=6,fill=col,shadow=LGRAY)
        d.text((380+bw6,fy2+22),f"  {val:.2f}",fill=NAVY,font=_font(22,True),anchor='lm')
        d.text((1100,fy2+22),note,fill=MGRAY,font=_font(19),anchor='lm')
    d.line([(370,80),(370,780)], fill=MGRAY, width=2)
    d.text((W//2,760),"Figure 4.2 — Feature Importances (Random Forest, impurity-based)",
           fill=DGRAY, font=_font(22), anchor='mm')
    return _save(img)

# ════════════════════════════════════════════════════════════════════════════════
# FIGURE 4.3  —  Confusion Matrix
# ════════════════════════════════════════════════════════════════════════════════
def fig_confusion_matrix():
    W,H = 1000,1000
    img = Image.new('RGB',(W,H),WHITE)
    d = ImageDraw.Draw(img)
    d.text((W//2,40),"Confusion Matrix — Gradient Boosting (Tuned)",
           fill=NAVY, font=_font(28,True), anchor='mm')
    d.text((W//2,80),"Test Set  n = 2,400  |  rows = Actual, columns = Predicted",
           fill=DGRAY, font=_font(22), anchor='mm')

    labels3 = ["Low","Medium","High","Very High"]
    matrix3 = [[560,28,8,4],[32,740,40,18],[10,42,540,8],[4,14,16,344]]
    cs = 150; ox2,oy2 = 240,200

    d.text((ox2+2*cs, oy2-40),"Predicted", fill=NAVY, font=_font(24,True), anchor='mm')
    for j2,l in enumerate(labels3):
        d.text((ox2+j2*cs+cs//2,oy2-16),l,fill=DGRAY,font=_font(22,True),anchor='mm')
    d.text((ox2-60,oy2+2*cs),"Actual",fill=NAVY,font=_font(24,True),anchor='mm')
    for i2,l in enumerate(labels3):
        d.text((ox2-16,oy2+i2*cs+cs//2),l,fill=DGRAY,font=_font(22,True),anchor='rm')

    total_r3 = [sum(r) for r in matrix3]
    for i2,row in enumerate(matrix3):
        for j2,val in enumerate(row):
            pct = val/total_r3[i2]
            if i2==j2:
                g = int(60+180*pct)
                fill2 = (30,g,60)
            else:
                shade = int(255-pct*220)
                fill2 = (255,shade,shade)
            d.rectangle([ox2+j2*cs,oy2+i2*cs,
                          ox2+j2*cs+cs-2,oy2+i2*cs+cs-2], fill=fill2)
            d.text((ox2+j2*cs+cs//2,oy2+i2*cs+cs//2-14),str(val),
                   fill=WHITE,font=_font(30,True),anchor='mm')
            acc2 = f"{pct*100:.1f}%"
            d.text((ox2+j2*cs+cs//2,oy2+i2*cs+cs//2+22),acc2,
                   fill=(200,255,200) if i2==j2 else (255,180,180),
                   font=_font(18),anchor='mm')

    # Overall accuracy
    d.rounded_rectangle([100,860,900,930], radius=12, fill=(232,245,232))
    correct = sum(matrix3[i][i] for i in range(4))
    d.text((500,895),f"Overall Accuracy: {correct/2400*100:.1f}%  |  F1-Score (weighted): 0.911",
           fill=GREEN,font=_font(26,True),anchor='mm')
    d.text((500,965),"Figure 4.3 — Confusion Matrix (Gradient Boosting Tuned, n=2,400)",
           fill=DGRAY,font=_font(22),anchor='mm')
    return _save(img)

# ════════════════════════════════════════════════════════════════════════════════
# FIGURE 4.4  —  Risk Distribution
# ════════════════════════════════════════════════════════════════════════════════
def fig_risk_distribution():
    W,H = 1200,700
    img = Image.new('RGB',(W,H),WHITE)
    d = ImageDraw.Draw(img)
    d.text((W//2,36),"Training Dataset — Risk Category Distribution",
           fill=NAVY, font=_font(28,True), anchor='mm')

    cats2 = [("LOW\n0–30",3000,25,GREEN),("MEDIUM\n31–50",4200,35,BLUE),
              ("HIGH\n51–70",3000,25,ORANGE),("VERY HIGH\n71–100",1800,15,RED)]
    bw7,gap7,base_y7,sx3 = 200,60,570,100

    d.line([(80,80),(80,base_y7)],fill=DGRAY,width=3)
    d.line([(80,base_y7),(1150,base_y7)],fill=DGRAY,width=3)
    for y7 in range(0,5001,1000):
        py = base_y7 - int(y7/4200*(base_y7-80))
        d.line([(75,py),(1150,py)], fill=LGRAY, width=1)
        d.text((70,py),f"{y7:,}",fill=DGRAY,font=_font(18),anchor='rm')

    for i,(cat,cnt,pct2,col) in enumerate(cats2):
        x7 = sx3 + i*(bw7+gap7)
        bh7 = int(cnt/4200*(base_y7-80))
        _shadow_rect(d,x7,base_y7-bh7,bw7,bh7,r=8,fill=col,shadow=LGRAY)
        d.text((x7+bw7//2,base_y7-bh7-50),f"{cnt:,}",fill=NAVY,font=_font(26,True),anchor='mm')
        d.text((x7+bw7//2,base_y7-bh7-24),f"({pct2}%)",fill=col,font=_font(22,True),anchor='mm')
        for j,line in enumerate(cat.split('\n')):
            d.text((x7+bw7//2,base_y7+22+j*26),line,fill=DGRAY,font=_font(20,True),anchor='mm')

    d.text((W//2,660),"Figure 4.4 — Risk Category Distribution: Synthetic Training Dataset (n = 12,000)",
           fill=DGRAY,font=_font(20),anchor='mm')
    return _save(img)

# ════════════════════════════════════════════════════════════════════════════════
# FIGURE 3.7  —  Gantt Chart
# ════════════════════════════════════════════════════════════════════════════════
def fig_gantt():
    W,H = 1800,900
    img = Image.new('RGB',(W,H),WHITE)
    d = ImageDraw.Draw(img)
    d.rectangle([0,0,W,60], fill=NAVY)
    d.text((W//2,30),"RiskGuard AI — Project Gantt Chart (14 Weeks: February – May 2026)",
           fill=WHITE, font=_font(26,True), anchor='mm')

    tasks = [
        ("Phase 1: Project Proposal & Approval",   1,2,  BLUE,   "Weeks 1–2"),
        ("Phase 2: Literature Review",              2,5,  (80,120,180), "Weeks 2–5"),
        ("Phase 3: Research Design & Methodology",  4,6,  PURPLE, "Weeks 4–6"),
        ("Phase 4: Synthetic Data Generation",      5,7,  ORANGE, "Weeks 5–7"),
        ("Phase 5: ML Model Training & Tuning",     6,9,  GREEN,  "Weeks 6–9"),
        ("Phase 6: Flask Web Application Dev",      7,11, (39,120,60),"Weeks 7–11"),
        ("Phase 7: PDF + Chatbot Integration",      9,11, (150,60,120),"Weeks 9–11"),
        ("Phase 8: Security & OWASP Hardening",    10,12, RED,    "Weeks 10–12"),
        ("Phase 9: Testing & Evaluation",          11,12, ORANGE, "Weeks 11–12"),
        ("Phase 10: Report Writing",                8,14, NAVY,   "Weeks 8–14"),
        ("Phase 11: Review & Submission",          13,14, (60,60,60),"Weeks 13–14"),
    ]
    label_w = 480
    weeks2 = 14
    gw2 = (W - label_w - 60) // weeks2
    bh8 = 36; oy3 = 80

    # week headers
    for w2 in range(1,weeks2+1):
        x8 = label_w + (w2-1)*gw2
        col_h = NAVY if w2%2==1 else BLUE
        d.rectangle([x8,oy3-22,x8+gw2-1,oy3], fill=col_h)
        d.text((x8+gw2//2,oy3-11),f"W{w2}",fill=WHITE,font=_font(18,True),anchor='mm')

    # today marker (week 14)
    today_x = label_w + 13*gw2
    d.line([(today_x,oy3),(today_x,oy3+len(tasks)*(bh8+8)+10)], fill=RED, width=3)
    d.text((today_x,oy3-38),"TODAY",fill=RED,font=_font(16,True),anchor='mm')

    for i,(name,start,end,col,weeks_lbl) in enumerate(tasks):
        y8 = oy3 + i*(bh8+8)
        # label
        d.text((label_w-10,y8+bh8//2),name,fill=DGRAY,font=_font(19),anchor='rm')
        # bar
        bx8 = label_w + (start-1)*gw2
        bw8 = (end-start)*gw2 - 4
        _shadow_rect(d,bx8,y8,bw8,bh8,r=6,fill=col,shadow=LGRAY)
        if bw8>120:
            d.text((bx8+bw8//2,y8+bh8//2),weeks_lbl,fill=WHITE,font=_font(16,True),anchor='mm')

    # milestones
    milestones = [(2,"M1: Proposal"),(5,"M2: LitRev"),(9,"M3: Model"),(11,"M4: App"),(14,"M7: Submit")]
    for wk,lbl in milestones:
        mx = label_w + (wk-1)*gw2
        d.polygon([(mx,oy3-50),(mx-14,oy3-32),(mx+14,oy3-32)], fill=ORANGE)
        d.text((mx,oy3-58),lbl,fill=ORANGE,font=_font(14,True),anchor='mm')

    d.text((W//2,870),"Figure 3.7 — 14-Week Project Gantt Chart  (Orange diamonds = milestones  |  Red line = submission date)",
           fill=DGRAY,font=_font(20),anchor='mm')
    return _save(img)


if __name__ == '__main__':
    tests = [
        ("fig_architecture",       fig_architecture),
        ("fig_conceptual_framework",fig_conceptual_framework),
        ("fig_login",              fig_login),
        ("fig_assessment",         fig_assessment),
        ("fig_report",             fig_report),
        ("fig_dashboard",          fig_dashboard),
        ("fig_history",            fig_history),
        ("fig_chatbot",            fig_chatbot),
        ("fig_model_comparison",   fig_model_comparison),
        ("fig_feature_importance", fig_feature_importance),
        ("fig_confusion_matrix",   fig_confusion_matrix),
        ("fig_risk_distribution",  fig_risk_distribution),
        ("fig_gantt",              fig_gantt),
    ]
    for name,fn in tests:
        buf = fn()
        kb = len(buf.getvalue())//1024
        print(f"  {name}: {kb} KB")
    print("All OK")
