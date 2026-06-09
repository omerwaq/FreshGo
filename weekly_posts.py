"""
Weekly auto-post generator for Fresh Go.
Cycles through 52 unique creative themes — one per week, year-round.
Each post uses the brand logo + packet image so identity is always present.
"""

import os
import asyncio
from datetime import datetime, timedelta

# ── 52 Weekly Themes ───────────────────────────────────────────────────────────
# Covers a full year of unique, non-repeating creative ideas.

WEEKLY_THEMES = [
    {"slug": "morning_ritual",      "topic": "Subah ki shuruat Fresh Go doodh ke sath — pure aur fresh start every day"},
    {"slug": "health_benefits",     "topic": "Fresh milk health benefits — strong bones, better immunity, natural protein"},
    {"slug": "pure_promise",        "topic": "Fresh Go ka wada: zero adulteration, no chemicals, bilkul pure cow milk"},
    {"slug": "farm_story",          "topic": "Behind the scenes at our Nankana Sahib farm — how we ensure freshness daily"},
    {"slug": "children_growth",     "topic": "Bachon ki growth ke liye Fresh Go milk — calcium, vitamins, natural goodness"},
    {"slug": "ghee_love",           "topic": "Desi ghee ka jadoo — cooking, taste aur health benefits of pure desi ghee"},
    {"slug": "delivery_promise",    "topic": "Farm se seedha ghar tak — Fresh Go delivers across Lahore every day"},
    {"slug": "winter_milk",         "topic": "Sardi mein garma garam doodh — Fresh Go winter warmth for your family"},
    {"slug": "fresh_vs_packet",     "topic": "Farm fresh vs packaged milk — Fresh Go wins on taste, purity aur nutrition"},
    {"slug": "friday_barkat",       "topic": "Juma Mubarak — start your blessed Friday with a glass of pure Fresh Go milk"},
    {"slug": "order_cta",           "topic": "Order Fresh Go milk now — WhatsApp 0300-3147887, delivery Lahore mein subah tak"},
    {"slug": "family_tradition",    "topic": "Family ko best do — Fresh Go pure dairy is a Pakistani family tradition"},
    {"slug": "happy_cows",          "topic": "Khush gaaye, better milk — how cow happiness equals milk quality at Fresh Go"},
    {"slug": "summer_lassi",        "topic": "Garmi mein thandhi lassi Fresh Go doodh se — refreshing aur natural"},
    {"slug": "protein_power",       "topic": "Natural protein powerhouse — why Fresh Go milk fuels your active lifestyle"},
    {"slug": "weekly_special",      "topic": "Is hafte ka khas offer — Fresh Go milk aur ghee par special discount"},
    {"slug": "no_hormones",         "topic": "Koi hormone nahi, koi preservative nahi — Fresh Go is 100% natural cow milk"},
    {"slug": "eid_celebration",     "topic": "Eid Mubarak — celebrate with Fresh Go pure ghee sewaiyyan aur doodh"},
    {"slug": "mothers_love",        "topic": "Maa jaisi purity — Fresh Go milk, pure as a mother's love for her family"},
    {"slug": "farm_sunrise",        "topic": "Fajr ke waqt farm — early morning milking process at our Nankana Sahib farm"},
    {"slug": "ghee_cooking",        "topic": "Asli desi ghee se pakao — biryani, halwa, karahi sab kuch taste ho jata hai double"},
    {"slug": "trust_years",         "topic": "Saalon ka bharosa — families across Lahore trust Fresh Go for pure dairy"},
    {"slug": "new_area",            "topic": "Naye ilaqe mein delivery — Fresh Go ab aur bhi areas mein available hai Lahore"},
    {"slug": "thank_you_customers", "topic": "Shukriya hamare loyal customers ka — Fresh Go family growing strong together"},
    {"slug": "diet_wellness",       "topic": "Healthy diet mein Fresh Go doodh — nutritionist recommend pure natural milk daily"},
    {"slug": "strong_bones",        "topic": "Haddiyan mazboot, joints healthy — calcium-rich Fresh Go milk for every age"},
    {"slug": "lush_farm",           "topic": "Hari bhari zameen, saaf pani, khush gaaye — Fresh Go farm in Nankana Sahib"},
    {"slug": "pure_taste",          "topic": "Asli swad wapas ao — Fresh Go ki woh doodh ki khushbu aur taste pakki hai"},
    {"slug": "whole_family",        "topic": "Poori family ke liye Fresh Go — bacha ho ya buzurg, sab ke liye zaroor"},
    {"slug": "ramadan_sehri",       "topic": "Ramadan Mubarak — sehri mein Fresh Go doodh se raat bhar ki energy"},
    {"slug": "winter_ghee",         "topic": "Sardi mein desi ghee ki chamak — Fresh Go ghee for winter warmth aur taste"},
    {"slug": "spring_fresh",        "topic": "Bahar aa gayi — Fresh Go farm mein naya season, naya doodh, naye flavours"},
    {"slug": "chai_milk",           "topic": "Chai mein Fresh Go doodh — asli doodh se chai ka swad alag hi hota hai"},
    {"slug": "immunity_boost",      "topic": "Quwwat e mamunat naturally — Fresh Go milk mein natural antibodies aur vitamins"},
    {"slug": "farmer_pride",        "topic": "Pakistani kisaan ka fakhr — Fresh Go ka doodh desi values ke sath delivered"},
    {"slug": "customer_story",      "topic": "Grahak ki kahani — real families sharing their love for Fresh Go dairy"},
    {"slug": "milking_journey",     "topic": "Doodh ka safar — farm se aapke glass tak, Fresh Go ka hygiene process"},
    {"slug": "baby_nutrition",      "topic": "Bacchon ke liye best — Fresh Go natural milk, no additives, pure nutrition"},
    {"slug": "elderly_strength",    "topic": "Buzurgon ki sehat aur strength — daily Fresh Go milk for healthy aging"},
    {"slug": "weekend_family",      "topic": "Weekend family time — Fresh Go doodh aur ghee ke sath khushiyan double ho"},
    {"slug": "monsoon_special",     "topic": "Barsaat ka mausam — Fresh Go garam doodh aur ghee toast for rainy days"},
    {"slug": "natural_fat",         "topic": "Qudrati cheeknat ka fark — Fresh Go desi ghee mein real natural fat, no shortcuts"},
    {"slug": "repeat_trust",        "topic": "Ek baar order karo, baar baar wapas ao — Fresh Go quality never disappoints"},
    {"slug": "whatsapp_easy",       "topic": "Sirf ek WhatsApp message — order Fresh Go milk easily on 0300-3147887"},
    {"slug": "pure_white",          "topic": "Safed aur shuddh — Fresh Go milk ka rang hi purity ki guarantee hai"},
    {"slug": "biryani_ghee",        "topic": "Biryani mein asli desi ghee — Fresh Go ghee se biryani ban jati hai legendary"},
    {"slug": "village_taste",       "topic": "Gaon ka asli swad ab sheher mein — Fresh Go brings village freshness to Lahore"},
    {"slug": "hygienic_process",    "topic": "Saaf, suthra, hygienic — Fresh Go farm-to-bottle process you can trust"},
    {"slug": "bulk_save",           "topic": "Zyada kharido, zyada bachao — Fresh Go bulk order discount for families"},
    {"slug": "loyalty_love",        "topic": "Purane grahak hain hamare asli hero — Fresh Go loves its loyal customers"},
    {"slug": "independence_milk",   "topic": "14 August Mubarak — Fresh Go pure Pakistani milk for independent Pakistan"},
    {"slug": "new_year_fresh",      "topic": "Naya saal, naya azm — start the year fresh with Fresh Go pure dairy"},
]


# ── Post Generator ─────────────────────────────────────────────────────────────

async def generate_weekly_post() -> dict:
    """
    Generate this week's branded post.
    Returns {text, image_url, topic, theme_slug}.
    Uses the saved packet image + logo for brand consistency.
    """
    from brand_assets import get_next_theme_index, get_packet_path, get_logo_path
    from image_gen import generate_image_prompt_via_ai, _make_product_ad, _try_together

    # Pick theme
    idx = get_next_theme_index() % len(WEEKLY_THEMES)
    theme = WEEKLY_THEMES[idx]
    topic = theme["topic"]

    print(f"[Weekly] Theme #{idx}: {theme['slug']}")

    # Generate post text via Groq
    post_text = await asyncio.to_thread(_generate_post_text, topic)

    # Build image with real packet + logo
    packet_path = get_packet_path()
    logo_path   = get_logo_path()
    image_url   = None

    if packet_path:
        prompt = generate_image_prompt_via_ai(topic)
        image_url = await asyncio.to_thread(_make_product_ad, packet_path, prompt, logo_path)

    # Fallback: AI-only image if no packet uploaded yet
    if not image_url:
        from image_gen import fetch_and_save_image
        image_url = await fetch_and_save_image(topic)

    return {
        "text":       post_text,
        "image_url":  image_url,
        "topic":      topic,
        "theme_slug": theme["slug"],
    }


def _generate_post_text(topic: str) -> str:
    """Call Groq to write creative weekly post text for the given topic."""
    try:
        from groq import Groq
        from dotenv import load_dotenv
        from prompts import POST_SYSTEM_PROMPT
        load_dotenv()

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": POST_SYSTEM_PROMPT},
                {"role": "user",   "content": f"Write a creative, unique weekly Facebook post about: {topic}"},
            ],
            max_tokens=300,
            temperature=0.9,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Weekly Post Text Fallback] {e}")
        return (
            f"Fresh Go ka salam! 🐄✨\n\n{topic}\n\n"
            "100% pure cow milk — 250 rs/litre, Lahore mein delivery!\n"
            "Order karo: WhatsApp 0300-3147887\n"
            "#FreshGo #PureMilk #Lahore #DesiGhee #FarmFresh"
        )


# ── Schedule Helper ────────────────────────────────────────────────────────────

def next_sunday_9am() -> datetime:
    """Return the datetime of the next Sunday at 09:00 AM PKT."""
    now = datetime.now()
    days_ahead = (6 - now.weekday()) % 7  # 6 = Sunday
    if days_ahead == 0 and now.hour >= 9:
        days_ahead = 7
    return now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
