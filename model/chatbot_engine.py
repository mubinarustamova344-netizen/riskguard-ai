# -*- coding: utf-8 -*-
"""
RiskBot — Intelligent AI Chatbot Engine
Supports: Google Gemini (free) → Anthropic Claude → Comprehensive FAQ fallback
"""
import re, os
from datetime import datetime

# ── AI providers ───────────────────────────────────────────────────────────────
try:
    from google import genai as _genai
    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False

try:
    import anthropic as _anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False

# ── System prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are RiskBot — the intelligent AI assistant embedded in RiskGuard AI, a professional road accident risk assessment platform for insurance companies. Built as a Pearson BTEC Level 6 Diploma project at PDP University, Tashkent.

## Platform Knowledge

**ML Model:** XGBoost (Tuned) — 85.22% accuracy, ROC-AUC 0.9738
**Comparison:** Decision Tree 73.1% | Logistic Regression 77.7% | Extra Trees 78.2% | Random Forest 81.0% | Gradient Boosting 85.0% | XGBoost 85.22%
**Dataset:** 30,000 synthetic records, 18 features (12 input + 6 engineered)
**Stack:** Python 3.13, Flask 3.0, scikit-learn 1.3, XGBoost 3.2, SQLite, Bootstrap 5.3

**Risk Score Scale:**
- 0–25 → Low Risk (premium multiplier 1.0×)
- 26–50 → Medium Risk (1.35×)
- 51–75 → High Risk (1.75×)
- 76–100 → Very High Risk (2.30×)

**Feature Impact on Score:**
- previous_accidents: +14 pts each
- traffic_violations: +5 pts each
- vehicle_type: motorcycle +18, sports +12, truck +4, suv +3, sedan/van 0
- primary_location: urban +7, highway +4, rural +2, suburban 0
- driving_experience <2 yrs: +18; <5 yrs: +8
- driver_age <25: +(25–age)×1.8 pts
- marital_status married: −2 pts
- credit_score <600: +penalty; >750: bonus

**App Features:** Assessment, Dashboard, History, PDF reports, AI Chatbot, Risk Comparison, Insurance Quote, Batch CSV Upload, Certificate, API Docs, Simulator, i18n (English/Uzbek)

## Behaviour Rules
- **Language:** always reply in the SAME language the user writes in — Uzbek for Uzbek messages, English for English
- **Format:** use markdown (bold, tables, lists, code) to make answers scannable
- **Tone:** expert but friendly; think of yourself as an insurance advisor who knows this platform deeply
- **Scope:** answer anything about insurance, ML, driving risk, the platform, or how scores are calculated
- **Context:** remember the conversation — refer back to earlier messages when relevant
- **Brevity:** keep answers focused; avoid padding; use tables when comparing multiple items"""

# ── Comprehensive FAQ Knowledge Base ──────────────────────────────────────────
FAQ = [
    # ── GREETING ──────────────────────────────────────────────────────────────
    {
        'id': 'greeting',
        'patterns': [
            r'\b(hello|hi|hey|good\s*(morning|afternoon|evening)|howdy)\b',
            r'\b(salom|assalom|xayrli|qalesan|qalay|yaxshimisiz|nima\s*gap|qandaysiz|hoy)\b',
        ],
        'response': (
            "Salom! Men **RiskBot** — RiskGuard AI ning aqlli yordamchisi. 👋\n\n"
            "🏆 **XGBoost** modeli — 85.22% aniqlik | ROC-AUC 0.9738\n"
            "📊 30,000 yozuv | 18 xususiyat | 6 model taqqoslash\n\n"
            "Quyidagi mavzularda yordam bera olaman:\n"
            "• Sug'urta xavfi va mukofotlari\n"
            "• ML model va natijalar\n"
            "• Xavfni kamaytirish maslahatlari\n"
            "• Platformaning barcha funksiyalari\n\n"
            "Savol bering — o'zbek yoki ingliz tilida! 🇺🇿🇬🇧"
        ),
    },
    # ── FAREWELL ──────────────────────────────────────────────────────────────
    {
        'id': 'farewell',
        'keywords': ['bye','goodbye','xayr','rahmat','tashakkur','sog\'ling','alvido','see you','take care'],
        'response': "Xayr! Xavfsiz haydang. RiskGuard AI doim xizmatda! 🛡️\nGoodbye! Drive safely — RiskGuard AI is available 24/7.",
    },
    # ── HELP ──────────────────────────────────────────────────────────────────
    {
        'id': 'help',
        'keywords': ['help','yordam','nima qila','ko\'mak','imkoniyat','what can you','guide','assist'],
        'response': (
            "**RiskBot — Imkoniyatlar:**\n\n"
            "🤖 **AI va Model:**\n"
            "• XGBoost 85.22% aniqlik, ROC-AUC 0.9738\n"
            "• 6 model taqqoslash (DT, LR, ET, RF, GB, XGBoost)\n"
            "• 18 xususiyat (12 asosiy + 6 engineered)\n\n"
            "📊 **Xavf baholash:**\n"
            "• Xavf ball tizimi (0–100)\n"
            "• Premium ko'paytuvchilar (1.0×–2.30×)\n"
            "• Omillar va ularning ta'siri\n\n"
            "🚗 **Sug'urta:**\n"
            "• Mukofot hisoblash\n"
            "• No-Claims Bonus (NCB)\n"
            "• Telematics/UBI sug'urta\n"
            "• Coverage turlari\n\n"
            "💡 Istalgan savolni bering — 24/7 javob beraman!"
        ),
    },
    # ── RISK SCORE ────────────────────────────────────────────────────────────
    {
        'id': 'risk_score',
        'keywords': ['risk score','xavf ball','risk bali','ball nima','score nima','0-100','nol dan yuz'],
        'response': (
            "**Xavf Ball Tizimi (Risk Score: 0–100)**\n\n"
            "| Kategoriya | Ball | Premium |\n"
            "|-----------|------|----------|\n"
            "| 🟢 **Low** | 0–25 | 1.0× (asosiy narx) |\n"
            "| 🟡 **Medium** | 26–50 | 1.35× (+35%) |\n"
            "| 🔴 **High** | 51–75 | 1.75× (+75%) |\n"
            "| 🟣 **Very High** | 76–100 | 2.30× (+130%) |\n\n"
            "**Ball qanday hisoblanadi?**\n"
            "XGBoost modeli 18 ta xususiyatni tahlil qiladi va har bir omilga ball beradi.\n"
            "Masalan: 1 ta avaria = +14 ball, motosikl = +18 ball, yoshi <25 = +(25-yosh)×1.8 ball.\n\n"
            "To'liq baholash uchun `/assessment` sahifasiga o'ting."
        ),
    },
    # ── ASSESSMENT ────────────────────────────────────────────────────────────
    {
        'id': 'assessment',
        'keywords': ['assess','baholash','hisoblash','risk hisob','check my risk','calculate','evaluate','start','boshlash','yangi baholash'],
        'response': (
            "**Yangi Risk Baholash:**\n\n"
            "1️⃣ **Assessment** sahifasiga o'ting (navigatsiyadan)\n"
            "2️⃣ **12 ta maydonni** to'ldiring:\n"
            "   • Yosh, tajriba, jins, oilaviy holat\n"
            "   • Mashina turi, yoshi, yillik masofa\n"
            "   • Avarialar, qoidabuzarliklar, kecha haydash\n"
            "   • Kredit bali, joylashuv\n"
            "3️⃣ **Calculate Risk** tugmasini bosing\n"
            "4️⃣ **Natija:** Ball, kategoriya, omillar, tavsiyalar, PDF\n\n"
            "📱 Yoki to'g'ridan-to'g'ri: `/assessment` ga o'ting."
        ),
    },
    # ── PREMIUM / MUKOFOT ─────────────────────────────────────────────────────
    {
        'id': 'premium',
        'keywords': ['premium','mukofot','narx','to\'lov','sug\'urta narxi','qancha','arzon','qimmat','how much','cost','price','reduce premium','kamaytir'],
        'response': (
            "**Sug'urta Mukofoti Hisoblash:**\n\n"
            "Mukofot = **Asosiy narx × Premium ko'paytuvchi**\n\n"
            "| Xavf darajasi | Ko'paytuvchi | Misol (£500 asosiy) |\n"
            "|--------------|--------------|---------------------|\n"
            "| 🟢 Low | **1.0×** | £500 |\n"
            "| 🟡 Medium | **1.35×** | £675 |\n"
            "| 🔴 High | **1.75×** | £875 |\n"
            "| 🟣 Very High | **2.30×** | £1,150 |\n\n"
            "**Mukofotni kamaytirish yo'llari:**\n"
            "✅ Telematics qurilma o'rnating → **10–25% chegirma**\n"
            "✅ NCB 5 yil saqlang → **55–65% chegirma**\n"
            "✅ Kredit balini 700+ ga olib boring\n"
            "✅ Yillik masofa 10,000 dan kam ushlab turing\n"
            "✅ Defensiv haydash kursini tugatib sertifikat oling\n\n"
            "**Insurance Quote** sahifasida aniq hisoblash mumkin!"
        ),
    },
    # ── COVERAGE ──────────────────────────────────────────────────────────────
    {
        'id': 'coverage',
        'keywords': ['coverage','cover','policy','qoplan','himoya','polisa','sug\'urta turi','third party','comprehensive','tpft','nima qoplanadi'],
        'response': (
            "**Sug'urta Turlari (Coverage Types):**\n\n"
            "🔹 **Third Party Only (TPO)**\n"
            "Minimal qonuniy talab. Faqat boshqa shaxsga yetkazilgan zarar.\n"
            "❌ O'z mashinangiz qoplanmaydi\n\n"
            "🔸 **Third Party, Fire & Theft (TPFT)**\n"
            "TPO + o'z mashinangiz o'g'irlik yoki yong'inga qarshi.\n"
            "✅ Narxi tejamli | ❌ O'z mashinangizning ta'miroti yo'q\n\n"
            "🔴 **Comprehensive (To'liq)**\n"
            "Hammasi qoplanadi: o'z mashinangiz, tibbiyot, hamma holat.\n"
            "✅ Eng keng himoya | Ko'proq narx\n\n"
            "**Tavsiya:**\n"
            "• Low Risk → TPFT (tejamli)\n"
            "• Medium Risk → TPFT yoki Comprehensive\n"
            "• High / Very High → **Comprehensive majburiy**"
        ),
    },
    # ── RISK FACTORS ──────────────────────────────────────────────────────────
    {
        'id': 'risk_factors',
        'keywords': ['risk factor','omil','ta\'sir','oshiradi','kamayadi','nima oshir','nima kamayt','what affect','influence','impact'],
        'response': (
            "**Xavf Omillari va Ta'siri:**\n\n"
            "⬆️ **Xavfni OSHIRUVCHI omillar:**\n"
            "| Omil | Qo'shimcha ball |\n"
            "|------|----------------|\n"
            "| Motosikl | **+18 ball** |\n"
            "| Sport mashina | **+12 ball** |\n"
            "| Har bir avaria | **+14 ball** |\n"
            "| Shahar haydash | **+7 ball** |\n"
            "| Tajriba <2 yil | **+18 ball** |\n"
            "| Yosh <25 (masalan 20) | **+9 ball** |\n"
            "| Har bir qoidabuzarlik | **+5 ball** |\n"
            "| Magistral | **+4 ball** |\n"
            "| Truck | **+4 ball** |\n"
            "| Kredit <600 | **+qo'shimcha** |\n\n"
            "⬇️ **Xavfni KAMAYTIRADIGAN omillar:**\n"
            "• Turmushqurgan: **-2 ball**\n"
            "• Kredit >750: chegirma\n"
            "• Sedan/Van: 0 qo'shimcha\n"
            "• Shahar tashqarisi: 0 qo'shimcha\n"
            "• Tajriba >10 yil: 0 qo'shimcha"
        ),
    },
    # ── ACCIDENTS ─────────────────────────────────────────────────────────────
    {
        'id': 'accidents',
        'keywords': ['accident','avaria','hodisa','to\'qnashuv','halokat','crash','claim','incident','baxtsiz hodisa','jarima'],
        'response': (
            "**Avariyalar — Xavf Ballga Ta'siri:**\n\n"
            "Avvalgi avariyalar eng kuchli prediktor:\n"
            "• 0 avaria: Qo'shimcha yo'q ✅\n"
            "• 1 avaria: **+14 ball**\n"
            "• 2 avaria: **+28 ball**\n"
            "• 3 avaria: **+42 ball**\n"
            "• 5 avaria: **+70 ball** (Very High daraja)\n\n"
            "**Avariya ta'sirini kamaytirish:**\n"
            "1. 🖥️ Telematics o'rnating — xavfsiz haydashni isbotlang\n"
            "2. 🎓 Defensiv haydash kursi → premium kamayadi\n"
            "3. ⏰ 3 yil davomida toza yozuv → accident forgiveness\n"
            "4. 🛡️ NCB Protection → 1–2 avariya bonusni yo'qotmaydi\n\n"
            "**Muhim:** So'nggi 3 yildagi avariyalar eng ko'p ta'sir qiladi."
        ),
    },
    # ── SAFE DRIVING ──────────────────────────────────────────────────────────
    {
        'id': 'safe_driving',
        'keywords': ['safe driving','xavfsiz haydash','kamaytir','yaxshila','maslahat','tips','advice','reduce risk','lower risk','nima qilsam','qanday yaxshi','how to reduce'],
        'response': (
            "**Xavf Ballini Kamaytirish — Top Maslahatlar:**\n\n"
            "🏆 **Eng ta'sirchan (katta o'zgarish):**\n"
            "1. Telematics qurilma → **10–25% chegirma**\n"
            "2. 3+ yil toza yozuv → **eng katta ta'sir**\n"
            "3. Kredit balini 700+ ga olib boring\n\n"
            "🚗 **Haydash odati:**\n"
            "• Tezlik chegarasini doim saqlang\n"
            "• Kechasi haydashni 20% dan kam ushlab turing\n"
            "• Yillik masofa 10,000 milyadan kam\n"
            "• Tez-tez tormoz bosishdan saqlaning\n\n"
            "🎓 **O'qish:**\n"
            "• IAM Advanced Motorists kursi\n"
            "• Defensiv haydash sertifikati\n"
            "• Pass Plus (yangi haydovchilar uchun)\n\n"
            "🚙 **Mashina:**\n"
            "• Sport/motosikldan sedan/vanga o'ting\n"
            "• ADAS xavfsizlik tizimlari\n"
            "• Shahar tashqarisida ko'proq haydash"
        ),
    },
    # ── XGBOOST / ML MODEL ────────────────────────────────────────────────────
    {
        'id': 'ml_model',
        'keywords': ['xgboost','model','algoritm','machine learning','ml','sun\'iy intellekt','ai model','gradient','random forest','decision tree','how it works','qanday ishlaydi','aniqlik','accuracy'],
        'response': (
            "**RiskGuard AI — ML Pipeline:**\n\n"
            "**6 ta model taqqoslandi:**\n"
            "| Model | Aniqlik | ROC-AUC |\n"
            "|-------|---------|----------|\n"
            "| Decision Tree | 73.1% | 0.871 |\n"
            "| Logistic Regression | 77.7% | 0.936 |\n"
            "| Extra Trees | 78.2% | 0.944 |\n"
            "| Random Forest | 81.0% | 0.958 |\n"
            "| Gradient Boosting | 85.0% | 0.973 |\n"
            "| 🏆 **XGBoost (Tuned)** | **85.22%** | **0.9738** |\n\n"
            "**Nima uchun XGBoost?**\n"
            "✅ L1/L2 regularizatsiya — overfitting yo'q\n"
            "✅ Parallel hisob-kitob — tez ishlaydi\n"
            "✅ Tabular ma'lumotlarda eng yaxshi\n\n"
            "**Pipeline:**\n"
            "1. EngineerFeatures (18 xususiyat yaratish)\n"
            "2. StandardScaler + OneHotEncoder\n"
            "3. GridSearchCV (32 kombo × 3-fold CV)\n"
            "4. XGBoost prediction + risk score\n\n"
            "To'liq natijalar: `/model-report` sahifasida"
        ),
    },
    # ── DATASET ───────────────────────────────────────────────────────────────
    {
        'id': 'dataset',
        'keywords': ['dataset','ma\'lumot to\'plam','yozuv','sintetik','30000','30 ming','trening','training data','nechta yozuv'],
        'response': (
            "**RiskGuard AI Dataset:**\n\n"
            "📊 **Ko'lam:** 30,000 sintetik yozuv\n"
            "🎯 **Taqsimot (Balanced):**\n"
            "• 🟢 Low Risk: 35% (10,500)\n"
            "• 🟡 Medium Risk: 35% (10,500)\n"
            "• 🔴 High Risk: 20% (6,000)\n"
            "• 🟣 Very High Risk: 10% (3,000)\n\n"
            "**Qanday yaratildi?**\n"
            "Haqiqiy sug'urta aktuarial formulalariga asoslangan algoritmik generatsiya.\n"
            "Har bir yozuv 12 ta xususiyat va 6 ta interaction effect dan iborat.\n\n"
            "**Feature Engineering (18 xususiyat):**\n"
            "• 12 ta asosiy kirish (user form)\n"
            "• 6 ta engineered: acc_per_exp, viol_per_exp, youth_risk,\n"
            "  senior_risk, risk_combo, high_risk_vehicle\n\n"
            "Train/Test split: 80/20 (24,000 / 6,000)"
        ),
    },
    # ── TELEMATICS ────────────────────────────────────────────────────────────
    {
        'id': 'telematics',
        'keywords': ['telematics','black box','qora quti','ubi','usage-based','kuzatuv','tracking device'],
        'response': (
            "**Telematics (Black Box) Sug'urta:**\n\n"
            "Qurilma haydash xulqini kuzatadi:\n"
            "📍 Tezlik | 🛑 Tormoz | 🔄 Burilish | 🌙 Vaqt | 📏 Masofa\n\n"
            "**Afzalliklari:**\n"
            "✅ Xavfsiz haydovchilar uchun **10–25% chegirma**\n"
            "✅ Yosh haydovchilar uchun ideal — tajribani isbotlash\n"
            "✅ Avariyadan keyin xavfsiz haydashni ko'rsatish\n"
            "✅ Haqiqiy haydash xulqiga asoslangan baho\n"
            "✅ Real-time fikr-mulohaza va tavsiyalar\n\n"
            "**Kamchiliklari:**\n"
            "❌ Yomon ball mukofotni oshirishi mumkin\n"
            "❌ Joylashuv kuzatuvi — maxfiylik muammosi\n\n"
            "**Kimga tavsiya etiladi?**\n"
            "🎯 High yoki Very High risk profillari uchun — eng yaxshi yechim!\n"
            "🎯 Birinchi yil haydovchilar uchun majburiy bo'lishi mumkin."
        ),
    },
    # ── YOUNG DRIVER ──────────────────────────────────────────────────────────
    {
        'id': 'young_driver',
        'keywords': ['young driver','yosh haydovchi','yangi haydovchi','birinchi bor','learner','student driver','17','18','19','20','21','22','23','24','first time','pass plus'],
        'response': (
            "**Yosh Haydovchilar (<25 yosh) — Maslahatlar:**\n\n"
            "🔴 Muammo: Statistik jihatdan yosh haydovchilar ko'proq avariyaga uchraydi.\n"
            "• 20 yoshli haydovchi: +(25-20)×1.8 = **+9 ball** qo'shimcha\n\n"
            "📉 **Chegirma imkoniyatlari:**\n"
            "• **Pass Plus** sxemasini bajaring → chegirma\n"
            "• **Good Student Discount** → akademik ko'rsatkich\n"
            "• **Telematics polisa** → **10–25% chegirma** xavfsiz haydashda\n"
            "• Ota-onaning polisasiga qo'shimcha haydovchi sifatida kirish\n\n"
            "🚗 **Mashina tanlash:**\n"
            "• ❌ Sport va motosikldan saqlaning (+12/+18 ball)\n"
            "• ✅ Kichik sedan yoki van tanlang (0 qo'shimcha)\n"
            "• Euro NCAP 5-yulduz sertifikati bo'lgan mashina\n\n"
            "📅 **Uzoq muddatli strategiya:**\n"
            "• Har toza yil — risk bali kamayadi\n"
            "• 3 yildan keyin NCB boshlaydi\n"
            "• 25 yoshdan so'ng chegirma avtomatik oshadi\n\n"
            "💡 RiskGuard AI da yosh haydovchi profilini baholang!"
        ),
    },
    # ── NCB ───────────────────────────────────────────────────────────────────
    {
        'id': 'ncb',
        'keywords': ['ncb','no claims','no-claims','chegirma','bonus','baxtsiz hodisasiz','claim-free','loyalty','discount'],
        'response': (
            "**No-Claims Bonus (NCB) — Baxtsiz Hodisasiz Bonus:**\n\n"
            "| Yil | Chegirma |\n"
            "|-----|----------|\n"
            "| 1 yil | **20–30%** |\n"
            "| 2 yil | **35–40%** |\n"
            "| 3 yil | **45–50%** |\n"
            "| 5+ yil | **55–65%** |\n\n"
            "**NCB ni himoya qilish (NCB Protection):**\n"
            "✅ Polisaga NCB Protection qo'shing\n"
            "✅ 1–2 avaria bonusni yo'qotmaydi\n"
            "✅ Kichik ta'mirlash uchun da'vo qilishdan oldin o'ylang\n\n"
            "**Muhim bilimlar:**\n"
            "• NCB **haydovchiga** bog'liq, mashinaga emas\n"
            "• Sug'urta kompaniyasini almashtirsangiz ham NCB saqlanadi\n"
            "• Boshqa odamning mashinasini haydash NCB ga ta'sir qilmaydi\n\n"
            "RiskGuard AI Insurance Quote sahifasida NCB chegirmasini hisoblang!"
        ),
    },
    # ── CREDIT SCORE ──────────────────────────────────────────────────────────
    {
        'id': 'credit_score',
        'keywords': ['credit score','kredit','kredit bali','kredit reyting','fico','moliyaviy','financial','credit rating'],
        'response': (
            "**Kredit Bali va Sug'urta:**\n\n"
            "Ko'plab sug'urta kompaniyalari kredit balini risk ko'rsatkichi sifatida ishlatadi:\n\n"
            "| Kredit Bali | Ta'sir |\n"
            "|-------------|--------|\n"
            "| 750+ | Preferred rate — maksimal chegirma ✅ |\n"
            "| 650–749 | Standart rate |\n"
            "| 550–649 | Kichik qo'shimcha (+5–10%) |\n"
            "| <550 | Muhim qo'shimcha (+15–25%) |\n\n"
            "**RiskGuard AI da:** kredit bali 18 xususiyatdan biri.\n"
            "700 dan yuqori → qo'shimcha chegirma.\n\n"
            "**Kredit balini yaxshilash:**\n"
            "✅ To'lovlarni o'z vaqtida to'lang\n"
            "✅ Kredit karta limitini 30% dan kam ushlab turing\n"
            "✅ Qisqa muddatda ko'p kredit so'rovidan saqlaning\n"
            "✅ Electoral roll ga ro'yxatdan o'ting"
        ),
    },
    # ── VEHICLE TYPES ─────────────────────────────────────────────────────────
    {
        'id': 'vehicle_types',
        'keywords': ['vehicle type','mashina turi','motosikl','motorcycle','sport mashina','sports car','suv','truck','sedan','van','qaysi mashina','risky car','xavfli mashina'],
        'response': (
            "**Mashina Turlari va Xavf Darajalari:**\n\n"
            "| Mashina | Qo'shimcha Ball | Sababi |\n"
            "|---------|-----------------|--------|\n"
            "| 🏍️ Motosikl | **+18 ball** | Himoya yo'q, og'ir jarohat |\n"
            "| 🏎️ Sport | **+12 ball** | Yuqori tezlik, qimmat ta'mirlash |\n"
            "| 🚛 Truck | **+4 ball** | Katta massa = katta zarar |\n"
            "| 🚙 SUV | **+3 ball** | Katta o'lcham, og'ir boshqaruv |\n"
            "| 🚗 Sedan | **0 ball** | Standart — eng yaxshi tanlov |\n"
            "| 🚐 Van | **0 ball** | Professional haydovchilar |\n\n"
            "**Tavsiya:**\n"
            "🎯 Yosh va yangi haydovchilar uchun: **Sedan yoki Van**\n"
            "🎯 High Risk profili uchun sport/motosikldan foydalanmang\n"
            "🎯 Euro NCAP 5-yulduz mashinalar sug'urta chegirmasi olishi mumkin"
        ),
    },
    # ── LOCATION ──────────────────────────────────────────────────────────────
    {
        'id': 'location',
        'keywords': ['location','joylashuv','shahar','qishloq','magistral','urban','rural','highway','suburban','city driving'],
        'response': (
            "**Haydash Joylashuvi va Xavf:**\n\n"
            "| Joylashuv | Qo'shimcha | Sababi |\n"
            "|-----------|------------|--------|\n"
            "| 🏙️ Urban (Shahar) | **+7 ball** | Ko'p transport, piyodalar, to'xtash-yurish |\n"
            "| 🛣️ Highway (Magistral) | **+4 ball** | Yuqori tezlik, og'ir avariyalar |\n"
            "| 🌳 Rural (Qishloq) | **+2 ball** | Tor yo'llar, hayvonlar |\n"
            "| 🏘️ Suburban | **0 ball** | Eng yaxshi balans |\n\n"
            "**Amaliy maslahat:**\n"
            "💡 Asosan shahar tashqarisida haydashingizni polisada ko'rsating!\n"
            "Shahar tarifi **15–20% qimmatroq** bo'lishi mumkin.\n\n"
            "**RiskGuard AI da:** Joylashuv 18 xususiyatdan biri sifatida XGBoost ga beriladi.\n"
            "Suburban dan Urban ga o'tish taxminan **7 ball** oshiradi."
        ),
    },
    # ── PDF REPORT ────────────────────────────────────────────────────────────
    {
        'id': 'pdf_report',
        'keywords': ['pdf','report','hisobot','download','yuklab','download report','pdf hisobot','generate'],
        'response': (
            "**PDF Hisobot Yaratish:**\n\n"
            "Baholash tugagandan so'ng:\n"
            "1. Natija sahifasida **'Download PDF'** tugmasini bosing\n"
            "2. Hisobot avtomatik yaratiladi va yuklanadi\n\n"
            "**PDF hisobotda:**\n"
            "📋 Haydovchi va mashina profili\n"
            "📊 Risk bali va kategoriyasi\n"
            "💰 Premium ko'paytuvchi va da'vo ehtimoli\n"
            "🔍 Omillar tahlili\n"
            "💡 Shaxsiy tavsiyalar\n"
            "🏷️ RiskGuard AI brendi bilan rasmiylashtirilgan\n\n"
            "**History sahifasida** barcha o'tgan baholashlarning PDF ni ham yuklab olish mumkin.\n\n"
            "Sertifikat ham yaratish mumkin: **/certificate/[ID]**"
        ),
    },
    # ── DASHBOARD ─────────────────────────────────────────────────────────────
    {
        'id': 'dashboard',
        'keywords': ['dashboard','analytics','statistika','grafik','chart','tahlil','jadval','diagramma'],
        'response': (
            "**Analytics Dashboard:**\n\n"
            "📊 **Ko'rsatkichlar:**\n"
            "• Jami baholashlar soni\n"
            "• Risk kategoriyasi taqsimoti\n"
            "• Model aniqlik metrika (XGBoost 85.22%, ROC-AUC 0.9738)\n"
            "• Oylik trend (line chart)\n\n"
            "📈 **Grafiklar:**\n"
            "• Yosh taqsimoti bar chart\n"
            "• Joylashuv va mashina turi statistikasi\n"
            "• Risk score taqsimoti\n"
            "• Real-time yangilanish (LIVE badge)\n\n"
            "🔗 Navigatsiyadan **Analytics Dashboard** ni bosing.\n"
            "CSV eksport ham mavjud: **Export CSV** tugmasi."
        ),
    },
    # ── BATCH UPLOAD ──────────────────────────────────────────────────────────
    {
        'id': 'batch',
        'keywords': ['batch','csv','bulk','ommaviy','ko\'p yozuv','bir nechta','mass upload','batch upload'],
        'response': (
            "**Batch CSV Upload — Ommaviy Baholash:**\n\n"
            "Bir vaqtda **10,000 gacha** haydovchini baholang:\n\n"
            "1. `/batch-upload` sahifasiga o'ting\n"
            "2. CSV faylni drag & drop qiling\n"
            "3. **Upload** tugmasini bosing\n"
            "4. Natija: saqlangan yozuv soni va xato hisoboti\n\n"
            "**CSV formati (12 ta ustun):**\n"
            "```\n"
            "driver_age, driving_experience, annual_mileage, vehicle_age,\n"
            "previous_accidents, traffic_violations, night_driving_pct,\n"
            "credit_score, vehicle_type, primary_location, marital_status, gender\n"
            "```\n\n"
            "Barcha natijalarni eksport qilish: `/api/export-csv`"
        ),
    },
    # ── COMPARISON ────────────────────────────────────────────────────────────
    {
        'id': 'comparison',
        'keywords': ['compare','comparison','taqqosla','ikki haydovchi','versus','vs','farq','two driver','solishtiruv'],
        'response': (
            "**Risk Comparison Tool:**\n\n"
            "Ikki haydovchi profilini bir vaqtda taqqoslang!\n\n"
            "**Ko'rsatadi:**\n"
            "📊 Ikkala profil risk ball va kategoriyasi\n"
            "📈 Head-to-head bar chart\n"
            "🏆 Har bir omil bo'yicha g'olib indikator\n"
            "🎯 Class probability chart\n\n"
            "**Foydalanish holatlari:**\n"
            "• Asosiy va qo'shimcha haydovchi taqqoslash\n"
            "• Yosh va tajribali haydovchi solishtirish\n"
            "• Bir xil haydovchi uchun ikki xil mashina\n"
            "• Segmentatsiya tahlili (sug'urta kompaniyalari uchun)\n\n"
            "🔗 Tools menyusidan **Risk Comparison** ni bosing."
        ),
    },
    # ── QUOTE ─────────────────────────────────────────────────────────────────
    {
        'id': 'quote',
        'keywords': ['quote','insurance quote','kotirovka','narx hisob','mukofot hisobla','calculate premium'],
        'response': (
            "**Insurance Quote Calculator:**\n\n"
            "Risk ballingiz asosida to'liq mukofot hisoblang:\n\n"
            "1. `/quote` sahifasiga o'ting\n"
            "2. Avvalgi assessment natijangizni kiriting yoki yangi baholang\n"
            "3. **NCB yillarini** kiriting (chegirma uchun)\n"
            "4. Yillik asosiy narxni kiriting\n"
            "5. **Hisoblash** tugmasini bosing\n\n"
            "**Hisoblash formulasi:**\n"
            "Yakuniy narx = Asosiy narx × Premium ko'paytuvchi × (1 − NCB chegirma)\n\n"
            "NCB chegirmalari:\n"
            "• 1 yil: 20–30% | 2 yil: 35–40% | 5+ yil: 55–65%"
        ),
    },
    # ── PLATFORM / ABOUT ──────────────────────────────────────────────────────
    {
        'id': 'platform',
        'keywords': ['riskguard','platform','loyiha','dastur haqida','nima bu','what is riskguard','technology','tech stack'],
        'response': (
            "**RiskGuard AI — Platforma haqida:**\n\n"
            "🎓 **Loyiha:** Pearson BTEC Level 6 Diploma in Digital Technologies\n"
            "   PDP University, Tashkent, O'zbekiston\n\n"
            "🛠️ **Texnologiyalar:**\n"
            "• Backend: **Python 3.13 + Flask 3.0**\n"
            "• ML: **scikit-learn 1.3 + XGBoost 3.2**\n"
            "• Database: **SQLite + SQLAlchemy**\n"
            "• Frontend: **Bootstrap 5.3 + Chart.js 4.4**\n"
            "• AI Chat: **Claude Sonnet 4.6 / Google Gemini** (+ regex fallback)\n\n"
            "📊 **ML Natijalar:**\n"
            "• XGBoost: **85.22% aniqlik, ROC-AUC 0.9738**\n"
            "• Dataset: 30,000 sintetik yozuv\n"
            "• Features: 18 (12 asosiy + 6 engineered)\n\n"
            "🔒 **Xavfsizlik:** CSRF, Rate Limiting, bcrypt, HTTPOnly cookies\n\n"
            "**Funksiyalar:** Assessment, Dashboard, History, PDF, Chatbot,\n"
            "Comparison, Quote, Batch Upload, Certificate, API Docs, Simulator"
        ),
    },
    # ── UZBEK LANGUAGE ────────────────────────────────────────────────────────
    {
        'id': 'uzbek',
        'keywords': ['o\'zbek','uzbek','uzbekcha','o\'zbekcha','uzb tilida','uzbek tili'],
        'response': (
            "Ha, men o'zbek tilida ham to'liq javob bera olaman! 🇺🇿\n\n"
            "O'zbek tilida quyidagi mavzularda savol bering:\n"
            "• Xavf bahosi va kategoriyalar\n"
            "• Sug'urta mukofoti va chegirmalar\n"
            "• Mashina tanlash va xavf omillari\n"
            "• XGBoost ML model natijalari\n"
            "• Yosh haydovchi maslahatlari\n"
            "• Telematics va No-Claims Bonus\n"
            "• Dashboard va platformaning barcha funksiyalari\n\n"
            "Savol bering — men 24/7 tayorman! 💬"
        ),
    },
    # ── FRAUD ─────────────────────────────────────────────────────────────────
    {
        'id': 'fraud',
        'keywords': ['fraud','soxta','aldov','false claim','ghost broker','fronting','staged accident'],
        'response': (
            "**Sug'urta Firibgarligi (Insurance Fraud):**\n\n"
            "UK sug'urta sanoatiga har yili **£1 milliard+** zarar yetkazadi.\n\n"
            "**Asosiy firibgarlik turlari:**\n"
            "• **Fronting** — asosiy haydovchi sifatida past risk kishi ko'rsatish\n"
            "• **Staged accidents** — sun'iy avariyalar\n"
            "• **Ghost broking** — soxta polisa sotish\n"
            "• **Inflated claims** — zarar miqdorini oshirib ko'rsatish\n\n"
            "**RiskGuard AI qanday yordam beradi?**\n"
            "ML modeli statistik anomaliyalarni aniqlaydi:\n"
            "• 19 yoshli + 0 km haydash profili flaglanadi\n"
            "• Kredit bali va risk faktori nomuvofiqliklar\n\n"
            "**Oqibatlari:**\n"
            "⚠️ Polisani bekor qilish va qora ro'yxatga olish\n"
            "⚠️ Jinoiy javobgarlik (10 yilgacha)\n"
            "⚠️ Keyingi sug'urta olishda qiyinchilik"
        ),
    },
    # ── API DOCS ──────────────────────────────────────────────────────────────
    {
        'id': 'api',
        'keywords': ['api','endpoint','rest api','api docs','developer','integration','json','swagger'],
        'response': (
            "**RiskGuard AI — REST API:**\n\n"
            "**Asosiy endpointlar:**\n"
            "```\n"
            "POST /api/assess        — Risk baholash\n"
            "GET  /api/stats         — Dashboard statistika\n"
            "GET  /api/history       — Baholash tarixi\n"
            "GET  /api/export-csv    — CSV eksport\n"
            "POST /api/compare       — Ikki profil taqqoslash\n"
            "POST /api/batch-upload  — Ommaviy CSV baholash\n"
            "POST /api/chat          — Chatbot\n"
            "GET  /api/model-metrics — ML model metrikalar\n"
            "```\n\n"
            "**To'liq dokumentatsiya:** `/api-docs` sahifasiga o'ting.\n\n"
            "Authentication: Flask-Login session cookie.\n"
            "Rate limiting: 60 req/min (API), 10 req/min (login)."
        ),
    },
    # ── SECURITY ──────────────────────────────────────────────────────────────
    {
        'id': 'security',
        'keywords': ['security','xavfsizlik','csrf','password','login','authentication','session','rate limit'],
        'response': (
            "**RiskGuard AI Xavfsizlik Choralari:**\n\n"
            "🔒 **Autentifikatsiya:**\n"
            "• Flask-Login session management\n"
            "• bcrypt parol hashing\n"
            "• 8 soatlik session muddati\n\n"
            "🛡️ **Himoya:**\n"
            "• CSRF tokenlar (Flask-WTF) barcha POST so'rovlarda\n"
            "• Rate limiting: 10 req/min login, 60 req/min API\n"
            "• HTTPOnly + SameSite=Lax cookie\n\n"
            "🔐 **HTTP Security Headers:**\n"
            "• X-Content-Type-Options: nosniff\n"
            "• X-Frame-Options: DENY (clickjacking himoyasi)\n"
            "• Referrer-Policy: strict-origin-when-cross-origin\n\n"
            "📝 **Logging:**\n"
            "• RotatingFileHandler (app.log, 1MB limit)\n"
            "• Barcha login urinishlari va muhim harakatlar loglanadi"
        ),
    },
    # ── GENERAL QUESTIONS ─────────────────────────────────────────────────────
    {
        'id': 'affirmative',
        'keywords': ['yes','ha','albatta','ok','okay','sure','mayli','yep','go ahead'],
        'response': "Zo'r! Qanday yordam bera olaman? 🚀",
    },
    {
        'id': 'negative',
        'keywords': ['no','yo\'q','kerak emas','bekor','nope','cancel','skip'],
        'response': "Mayli, boshqa savol bo'lsa men doim shu yerdaman! 😊",
    },
    {
        'id': 'thanks',
        'keywords': ['thanks','thank you','rahmat','tashakkur','rakhmat','minnatdorman','great','perfect','zo\'r','yaxshi'],
        'response': "Xush kelibsiz! 😊 Boshqa savol bo'lsa, men 24/7 tayorman. Xavfsiz haydang! 🚗",
    },
]

# Default response when nothing matches
DEFAULT_RESPONSE = (
    "Savolingiz uchun rahmat! Men quyidagilarda yordam bera olaman:\n\n"
    "📋 **Tez-tez so'raladigan savollar:**\n"
    "• `xavf ball nima?` — Risk score tizimi haqida\n"
    "• `mukofot qanday hisoblanadi?` — Premium tizimi\n"
    "• `XGBoost nima?` — ML model natijasi\n"
    "• `xavfni qanday kamaytiray?` — Amaliy maslahatlar\n"
    "• `yosh haydovchi uchun maslahat` — NCB, telematics\n"
    "• `telematics nima?` — Black box sug'urta\n"
    "• `coverage turlari` — TPO, TPFT, Comprehensive\n"
    "• `dataset haqida` — 30,000 yozuv, 18 xususiyat\n"
    "• `batch upload` — CSV ommaviy baholash\n\n"
    "Ingliz yoki o'zbek tilida yozing — men 24/7 tayorman! 🤖"
)


# ── RiskChatbot class ──────────────────────────────────────────────────────────
class RiskChatbot:
    def __init__(self):
        self.conversation_history = []

        # ── Gemini (free) ───────────────────────────────────────────────────
        gemini_key = os.environ.get('GEMINI_API_KEY', '').strip()
        if _GEMINI_AVAILABLE and gemini_key:
            try:
                self._gemini_client = _genai.Client(api_key=gemini_key)
                self._use_gemini = True
            except Exception:
                self._gemini_client = None
                self._use_gemini = False
        else:
            self._gemini_client = None
            self._use_gemini = False

        # ── Claude (when credits available) ────────────────────────────────
        claude_key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
        if _ANTHROPIC_AVAILABLE and claude_key:
            try:
                self._claude_client = _anthropic.Anthropic(api_key=claude_key)
                self._use_claude = True
            except Exception:
                self._claude_client = None
                self._use_claude = False
        else:
            self._claude_client = None
            self._use_claude = False

        self._use_ai = self._use_gemini or self._use_claude

    @property
    def ai_enabled(self):
        return self._use_ai

    def _find_faq(self, message: str) -> str | None:
        """Two-pass FAQ lookup: regex patterns then substring keywords."""
        msg = message.lower().strip()

        # Pass 1: regex
        for faq in FAQ:
            for pattern in faq.get('patterns', []):
                if re.search(pattern, msg, re.IGNORECASE):
                    return faq['response']

        # Pass 2: substring keywords
        for faq in FAQ:
            for kw in faq.get('keywords', []):
                if kw.lower() in msg:
                    return faq['response']

        return None

    def _gemini_chat(self, user_message: str) -> str:
        history_text = ""
        for entry in self.conversation_history[-6:]:
            role = "User" if entry['role'] == 'user' else "Assistant"
            history_text += f"{role}: {entry['message']}\n"

        prompt = f"{SYSTEM_PROMPT}\n\n{history_text}User: {user_message}\nAssistant:"
        response = self._gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return response.text

    def _claude_chat(self, user_message: str) -> str:
        messages = []
        for entry in self.conversation_history[-10:]:
            messages.append({
                'role': 'user' if entry['role'] == 'user' else 'assistant',
                'content': entry['message']
            })
        messages.append({'role': 'user', 'content': user_message})
        response = self._claude_client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=1200,
            system=[{"type": "text", "text": SYSTEM_PROMPT,
                     "cache_control": {"type": "ephemeral"}}],
            messages=messages,
        )
        return response.content[0].text

    def stream_chat(self, user_message: str):
        """Yield text chunks for streaming response."""
        # 1. FAQ match → instant, language-correct response
        faq_response = self._find_faq(user_message)
        if faq_response:
            self._save_history(user_message, faq_response, 'faq')
            yield faq_response
            return

        # 2. Try Gemini for unrecognised queries
        if self._use_gemini:
            try:
                result = self._gemini_chat(user_message)
                self._save_history(user_message, result, 'gemini')
                yield result
                return
            except Exception:
                pass

        # 3. Try Claude for unrecognised queries
        if self._use_claude:
            full = ''
            try:
                messages = []
                for entry in self.conversation_history[-10:]:
                    messages.append({
                        'role': 'user' if entry['role'] == 'user' else 'assistant',
                        'content': entry['message'],
                    })
                messages.append({'role': 'user', 'content': user_message})
                with self._claude_client.messages.stream(
                    model='claude-sonnet-4-6', max_tokens=1200,
                    system=[{"type": "text", "text": SYSTEM_PROMPT,
                             "cache_control": {"type": "ephemeral"}}],
                    messages=messages,
                ) as stream:
                    for text in stream.text_stream:
                        full += text
                        yield text
                self._save_history(user_message, full, 'claude')
                return
            except Exception:
                pass

        # 4. Default fallback
        self._save_history(user_message, DEFAULT_RESPONSE, 'faq')
        yield DEFAULT_RESPONSE

    def chat(self, user_message: str) -> dict:
        """Non-streaming chat for /api/chat endpoint."""
        # 1. FAQ match → instant, language-correct response
        faq_response = self._find_faq(user_message)
        if faq_response:
            self._save_history(user_message, faq_response, 'faq')
            return {
                'response': faq_response,
                'intent': 'faq',
                'ai_powered': self._use_ai,
                'timestamp': datetime.now().strftime('%H:%M'),
            }

        intent = 'default'
        response = None

        if self._use_gemini:
            try:
                response = self._gemini_chat(user_message)
                intent = 'gemini'
            except Exception:
                pass

        if response is None and self._use_claude:
            try:
                response = self._claude_chat(user_message)
                intent = 'claude'
            except Exception:
                pass

        if response is None:
            response = DEFAULT_RESPONSE

        self._save_history(user_message, response, intent)
        return {
            'response': response,
            'intent': intent,
            'ai_powered': self._use_ai,
            'timestamp': datetime.now().strftime('%H:%M'),
        }

    def _save_history(self, user_msg: str, bot_msg: str, intent: str):
        ts = datetime.now().isoformat()
        self.conversation_history.extend([
            {'role': 'user', 'message': user_msg, 'timestamp': ts},
            {'role': 'bot',  'message': bot_msg,  'intent': intent, 'timestamp': ts},
        ])
        # Keep last 20 turns
        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-40:]

    def reset(self):
        self.conversation_history = []
