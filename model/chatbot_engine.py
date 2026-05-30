import re
from datetime import datetime

INTENTS = {
    'greeting': [
        r'\b(hello|hi|hey|good (morning|afternoon|evening)|howdy|greetings)\b'
    ],
    'farewell': [
        r'\b(bye|goodbye|see you|take care|exit|quit)\b'
    ],
    'help': [
        r'\b(help|what can you do|how does this work|guide me|assist)\b'
    ],
    'start_assessment': [
        r'\b(assess|assessment|check my risk|calculate|evaluate|quote|get a quote|start)\b'
    ],
    'ask_premium': [
        r'\b(premium|cost|price|how much|payment|monthly|annual fee|charge)\b'
    ],
    'ask_coverage': [
        r'\b(coverage|cover|policy|what.s covered|include|protect)\b'
    ],
    'ask_risk_factors': [
        r'\b(risk factor|risk factors|what affect|what increase|what lower|what reduce|influence|impact|factor)\b'
    ],
    'ask_accidents': [
        r'\b(accident|crash|claim|incident|collision)\b'
    ],
    'ask_safe_driving': [
        r'\b(safe driving|drive safely|improve|reduce risk|lower risk|tips|advice)\b'
    ],
    'ask_model': [
        r'\b(model|algorithm|machine learning|how it works|prediction|ai|how do you)\b'
    ],
    'ask_telematics': [
        r'\b(telematics|black box|tracking device|ubi|usage.based)\b'
    ],
    'ask_young_driver': [
        r'\b(young driver|new driver|first time|learner|provisional|student driver)\b'
    ],
    'ask_no_claims': [
        r'\b(no claims|ncb|no claim bonus|discount|reward|loyalty)\b'
    ],
    'ask_excess': [
        r'\b(excess|deductible|out.of.pocket|self.insure|pay.when.claim)\b'
    ],
    'ask_credit_score': [
        r'\b(credit score|credit rating|credit check|fico|financial history)\b'
    ],
    'ask_comparison': [
        r'\b(compare|comparison|versus|vs|difference between|which is better|two driver)\b'
    ],
    'ask_vehicle_risk': [
        r'\b(sports car|motorcycle|suv|truck|sedan|which vehicle|risky car|safe car)\b'
    ],
    'ask_location_risk': [
        r'\b(city driving|urban risk|rural driving|highway risk|where to drive|location affect)\b'
    ],
    'ask_fraud': [
        r'\b(fraud|fake claim|insurance fraud|false claim|ghost broker)\b'
    ],
    'affirmative': [
        r'\b(yes|yeah|yep|sure|ok|okay|go ahead|proceed|correct|right)\b'
    ],
    'negative': [
        r'\b(no|nope|not now|cancel|skip|later)\b'
    ],
}

RESPONSES = {
    'greeting': [
        "Hello! I'm RiskBot, your AI insurance risk assistant. I can help you assess road accident risk, explain your insurance options, and provide personalised recommendations. How can I help you today?",
        "Hi there! Welcome to the Risk Assessment System for Insurance. I can evaluate your driving risk profile, explain premium factors, or answer questions about your coverage. What would you like to know?",
    ],
    'farewell': [
        "Goodbye! Drive safely and feel free to return anytime for a risk assessment. Stay safe on the roads!",
        "Take care! Remember, maintaining a clean driving record is your best way to keep premiums low. Bye!",
    ],
    'help': [
        "Here's what I can help you with:\n\n"
        "🔹 **Risk Assessment** – Get your personalised road risk score\n"
        "🔹 **Premium Factors** – Learn what affects your insurance cost\n"
        "🔹 **Safe Driving Tips** – Advice to reduce your risk profile\n"
        "🔹 **Coverage Information** – Understand what policies cover\n"
        "🔹 **Young Driver Advice** – Special guidance for new drivers\n"
        "🔹 **No-Claims Bonus** – How to protect your discount\n\n"
        "You can also use the **Risk Assessment Form** in the navigation menu for a full evaluation. What would you like to explore?",
    ],
    'start_assessment': [
        "Great! To give you an accurate risk assessment, please use the **Risk Assessment** page from the navigation menu. It will collect your driver profile, vehicle details, and driving habits, then generate your personalised risk score with recommendations.\n\nAlternatively, I can answer any questions about the process here. What would you like to know first?",
    ],
    'ask_premium': [
        "Your insurance premium is calculated based on your **risk score**, which considers:\n\n"
        "• **Driver factors**: Age, experience, accident history, violations\n"
        "• **Vehicle factors**: Type, age, safety features\n"
        "• **Behavioural factors**: Annual mileage, night driving percentage\n"
        "• **Environmental factors**: Primary driving location\n\n"
        "Our model applies a premium multiplier:\n"
        "- Low Risk: **1.0× base rate** (no surcharge)\n"
        "- Medium Risk: **1.35×** base rate\n"
        "- High Risk: **1.75×** base rate\n"
        "- Very High Risk: **2.30×** base rate\n\n"
        "Would you like to run a full assessment to see your personal multiplier?",
    ],
    'ask_coverage': [
        "Our insurance policies offer three main coverage tiers:\n\n"
        "🔹 **Third Party Only** – Minimum legal requirement. Covers damage to others.\n"
        "🔹 **Third Party, Fire & Theft** – Adds protection against vehicle theft and fire damage.\n"
        "🔹 **Comprehensive** – Full coverage including own damage, medical expenses, and more.\n\n"
        "Coverage limits and exclusions vary by policy. For personalised recommendations, run a risk assessment first — it helps us match you with the most suitable policy tier. Shall I guide you through the assessment?",
    ],
    'ask_risk_factors': [
        "The key factors that **increase** your risk score include:\n\n"
        "⬆️ Young age (under 25) or older age (over 65)\n"
        "⬆️ Limited driving experience (under 2 years)\n"
        "⬆️ Previous accident history\n"
        "⬆️ Traffic violations (speeding, running red lights)\n"
        "⬆️ High annual mileage (over 30,000 miles)\n"
        "⬆️ High percentage of night-time driving\n"
        "⬆️ High-risk vehicles (sports cars, motorcycles)\n"
        "⬆️ Urban driving environment\n"
        "⬆️ Low credit score\n\n"
        "Factors that **reduce** your risk include clean records, telematics devices, and advanced driver training. Want specific tips for your profile?",
    ],
    'ask_accidents': [
        "Accident history is one of the **strongest predictors** of future claims in our model.\n\n"
        "Here's how previous accidents affect your score:\n"
        "• 0 accidents: No surcharge (baseline)\n"
        "• 1 accident: +14 points on risk score\n"
        "• 2 accidents: +28 points\n"
        "• 3+ accidents: Significant impact — may trigger manual underwriting review\n\n"
        "**To mitigate this impact:**\n"
        "✅ Install a telematics (black box) device to demonstrate safe driving\n"
        "✅ Complete an approved defensive driving course\n"
        "✅ Maintain a clean record for 3+ years for accident forgiveness\n\n"
        "Claims within the past 3 years have the most significant impact. Would you like more information?",
    ],
    'ask_safe_driving': [
        "Here are evidence-based tips to **improve your risk profile and reduce premiums**:\n\n"
        "🚗 **Driving Behaviour:**\n"
        "• Maintain consistent speeds and avoid harsh braking\n"
        "• Follow speed limits strictly — violations add significant risk points\n"
        "• Reduce night-time driving where possible\n\n"
        "📱 **Technology:**\n"
        "• Install a telematics device for usage-based insurance (UBI) — can save 10–25%\n"
        "• Use advanced driver assistance systems (ADAS)\n\n"
        "🎓 **Training:**\n"
        "• Complete an IAM (Institute of Advanced Motorists) course\n"
        "• Defensive driving courses recognised by most insurers\n\n"
        "🔧 **Vehicle Maintenance:**\n"
        "• Keep tyres at correct pressure and replace when worn\n"
        "• Ensure all lights are functional\n\n"
        "Over time, a clean record (3+ years) is the single most impactful change you can make. Any specific area you'd like to explore?",
    ],
    'ask_model': [
        "Our risk assessment engine uses a **Random Forest Classifier** trained on 12,000 synthetic records that reflect real-world insurance data patterns.\n\n"
        "**How it works:**\n"
        "1. You submit your driver and vehicle profile\n"
        "2. Features are preprocessed (scaling + one-hot encoding)\n"
        "3. The model predicts your risk category across 4 classes\n"
        "4. A deterministic risk score (0–100) is computed from domain rules\n"
        "5. Recommendations are generated based on your specific risk factors\n\n"
        "**Model Performance:**\n"
        "• Typical accuracy: ~87–91% on test data\n"
        "• Cross-validated with 5-fold CV\n"
        "• Compared against Decision Tree, Logistic Regression, and Gradient Boosting\n\n"
        "The key features by importance are: previous accidents, driving experience, driver age, traffic violations, and annual mileage. Want to see the full dashboard with model metrics?",
    ],
    'ask_telematics': [
        "**Telematics insurance** (also called Usage-Based Insurance or UBI) uses a black box device or smartphone app to monitor your actual driving behaviour.\n\n"
        "**What is monitored:**\n"
        "• Speed and acceleration patterns\n"
        "• Braking intensity\n"
        "• Cornering behaviour\n"
        "• Time of day driving\n"
        "• Distance driven\n\n"
        "**Benefits:**\n"
        "✅ Can reduce premiums by **10–25%** for safe drivers\n"
        "✅ Particularly beneficial for young drivers with no history\n"
        "✅ Provides real-time feedback to improve driving habits\n"
        "✅ Proves safe behaviour after a previous accident\n\n"
        "**Drawbacks:**\n"
        "❌ Poor scores can increase your premium\n"
        "❌ Privacy concerns around location tracking\n\n"
        "Recommended especially if your risk score is 'High' or above. Would you like to know more?",
    ],
    'ask_young_driver': [
        "Young drivers (under 25) face higher premiums due to statistically higher accident rates. Here's how to manage costs:\n\n"
        "📉 **Discount Opportunities:**\n"
        "• Pass Plus scheme completion\n"
        "• Good Student Discount (with academic proof)\n"
        "• Telematics/black box policy\n"
        "• Being added as a named driver on parents' policy\n\n"
        "🚗 **Vehicle Choice Matters:**\n"
        "• Lower-powered, smaller engine vehicles reduce premiums significantly\n"
        "• Avoid sports cars and motorcycles as a first vehicle\n"
        "• A car with good safety ratings (Euro NCAP 5-star) helps\n\n"
        "📅 **Building a Record:**\n"
        "• Every clean year reduces your risk score\n"
        "• After 3 years with no claims, you qualify for No-Claims Bonus\n\n"
        "Would you like a risk assessment tailored for a young driver profile?",
    ],
    'ask_no_claims': [
        "The **No-Claims Bonus (NCB)** is one of the most valuable discounts in motor insurance.\n\n"
        "**How it builds:**\n"
        "• 1 year claim-free: ~20–30% discount\n"
        "• 2 years: ~35–40%\n"
        "• 3 years: ~45–50%\n"
        "• 5+ years: ~55–65% discount\n\n"
        "**Protecting your NCB:**\n"
        "✅ NCB Protection add-on allows 1–2 at-fault claims without losing the bonus\n"
        "✅ Consider whether to claim for small repairs (excess vs premium increase)\n\n"
        "**Important:** NCB follows the driver, not the vehicle. It transfers between insurers.\n\n"
        "In our risk model, drivers with 0 previous accidents receive the maximum baseline discount. Want to calculate how your NCB affects your premium?",
    ],
    'ask_excess': [
        "The **policy excess** (or deductible) is the amount YOU pay when making a claim before the insurer covers the rest.\n\n"
        "**Two types of excess:**\n"
        "• **Compulsory excess** – Set by the insurer, typically £100–£500 depending on risk profile\n"
        "• **Voluntary excess** – You can choose to add extra to lower your premium\n\n"
        "**Example:** If your car suffers £800 damage and your total excess is £300, the insurer pays £500.\n\n"
        "**Strategy:** Increasing voluntary excess from £0 to £250 can reduce your annual premium by **8–15%**, but only if you can afford to pay it in an emergency.\n\n"
        "In our risk model, higher-risk drivers are typically assigned higher compulsory excess amounts. Would you like to know how your risk score affects your excess?",
    ],
    'ask_credit_score': [
        "Your **credit score** is used by many UK insurers as a risk indicator — drivers with poor credit are statistically more likely to make claims.\n\n"
        "**How it affects your premium:**\n"
        "• Score 750+: Preferred rate — maximum discount\n"
        "• Score 650–749: Standard rate\n"
        "• Score 550–649: Small surcharge (+5–10%)\n"
        "• Score below 550: Significant surcharge (+15–25%)\n\n"
        "**In our ML model**, credit score is included as a feature. Raising it above 700 removes the surcharge entirely.\n\n"
        "**How to improve your score:**\n"
        "✅ Pay bills on time\n"
        "✅ Keep credit card utilisation below 30%\n"
        "✅ Avoid multiple credit applications in a short period\n"
        "✅ Register on the electoral roll\n\n"
        "Would you like to run a risk assessment to see how your current score affects your result?",
    ],
    'ask_comparison': [
        "Our **Risk Comparison Tool** lets you compare two driver profiles side-by-side!\n\n"
        "It shows:\n"
        "• Both risk scores and categories\n"
        "• Head-to-head bar chart of key metrics\n"
        "• Factor-by-factor comparison table with a winner indicator\n"
        "• Class probability charts for each driver\n\n"
        "Common use cases for insurers:\n"
        "• Compare a named driver vs main policyholder\n"
        "• Evaluate a young driver vs experienced driver\n"
        "• Compare two vehicles for the same driver\n\n"
        "Visit the **Risk Comparison Tool** from the Tools menu in the navigation bar. Would you like to know more about how the comparison works?",
    ],
    'ask_vehicle_risk': [
        "Different vehicle types carry significantly different insurance risk. Here's our model's vehicle risk ranking:\n\n"
        "🏍️ **Motorcycle** – Highest risk (+18 pts). No protective bodywork, severe injuries likely in accidents.\n"
        "🏎️ **Sports Car** – Very high risk (+12 pts). High speeds, younger demographic, expensive to repair.\n"
        "🚛 **Truck** – Elevated risk (+4 pts). Higher mass = more damage in collisions.\n"
        "🚙 **SUV** – Moderate risk (+3 pts). Larger footprint, higher centre of gravity.\n"
        "🚗 **Sedan** – Baseline risk (0 pts). Most common, well-studied risk profile.\n"
        "🚐 **Van** – Baseline risk (0 pts). Typically commercial use, professional drivers.\n\n"
        "**Recommendation:** For new or young drivers, starting with a **sedan or van** significantly reduces premiums.\n\n"
        "Would you like to calculate the premium difference between two vehicle types?",
    ],
    'ask_location_risk': [
        "Where you drive matters as much as how you drive. Here's how location affects your risk score in our model:\n\n"
        "🏙️ **Urban (City)** – Highest risk (+7 pts)\n"
        "   Higher traffic density, more pedestrians, frequent stop-start driving\n\n"
        "🛣️ **Highway / Motorway** – Elevated risk (+4 pts)\n"
        "   High speeds mean more severe accidents, though frequency is lower\n\n"
        "🌳 **Rural** – Low risk (+2 pts)\n"
        "   Lower traffic, but narrow roads and wildlife hazards\n\n"
        "🏘️ **Suburban** – Baseline risk (0 pts)\n"
        "   Best balance of low traffic and good road conditions\n\n"
        "**Insurer tip:** If you drive mostly in suburban or rural areas, make sure this is reflected in your policy declaration — urban rates can be 15–20% higher.\n\n"
        "Would you like to run an assessment with your specific location?",
    ],
    'ask_fraud': [
        "**Insurance fraud** is a serious issue costing the UK insurance industry over £1 billion per year, which ultimately raises premiums for honest drivers.\n\n"
        "**Common types of fraud our system helps detect:**\n"
        "• **Fronting** – Named a lower-risk driver as main policyholder\n"
        "• **Staged accidents** – Deliberate collisions to claim\n"
        "• **Ghost broking** – Fake policies sold by unlicensed brokers\n"
        "• **Inflated claims** – Exaggerating damage or injury\n\n"
        "**How RiskGuard AI helps:**\n"
        "Our ML model flags inconsistencies between declared profile and statistical norms — for example, a 19-year-old declaring very low mileage with zero night driving in an urban area would be flagged for review.\n\n"
        "**Consequences of fraud:**\n"
        "⚠️ Policy cancellation and blacklisting\n"
        "⚠️ Criminal prosecution (up to 10 years imprisonment)\n"
        "⚠️ Difficulty obtaining future insurance\n\n"
        "Is there anything specific about fraud detection you'd like to know?",
    ],
    'affirmative': [
        "Great! Please head to the **Risk Assessment** section using the navigation menu above, or I can answer more questions here. What would you like to do?",
    ],
    'negative': [
        "No problem! I'm here whenever you're ready. Is there anything else I can help you with?",
    ],
    'default': [
        "I'm not sure I fully understood that. I can help you with:\n\n"
        "• **Risk Assessment** – Check your driving risk score\n"
        "• **Premiums** – Understand your insurance costs\n"
        "• **Safe Driving** – Tips to lower your risk\n"
        "• **Coverage** – Learn about policy options\n"
        "• **Young Drivers** – Advice for new drivers\n\n"
        "Try asking something like: *'What factors affect my premium?'* or *'How can I reduce my risk score?'*",
    ],
}


class RiskChatbot:
    def __init__(self):
        self.conversation_history = []
        self.response_indices = {intent: 0 for intent in RESPONSES}

    def detect_intent(self, message: str) -> str:
        msg = message.lower().strip()
        for intent, patterns in INTENTS.items():
            for pattern in patterns:
                if re.search(pattern, msg):
                    return intent
        return 'default'

    def get_response(self, intent: str) -> str:
        responses = RESPONSES.get(intent, RESPONSES['default'])
        idx = self.response_indices.get(intent, 0) % len(responses)
        self.response_indices[intent] = (idx + 1) % len(responses)
        return responses[idx]

    def chat(self, user_message: str) -> dict:
        intent = self.detect_intent(user_message)
        response = self.get_response(intent)
        self.conversation_history.append({
            'role': 'user',
            'message': user_message,
            'timestamp': datetime.now().isoformat(),
        })
        self.conversation_history.append({
            'role': 'bot',
            'message': response,
            'intent': intent,
            'timestamp': datetime.now().isoformat(),
        })
        return {
            'response': response,
            'intent': intent,
            'timestamp': datetime.now().strftime('%H:%M'),
        }

    def reset(self):
        self.conversation_history = []
