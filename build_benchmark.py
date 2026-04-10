"""
TravelQA Benchmark Builder

Scrapes WikiVoyage for 30+ countries, extracts travel knowledge sections,
and generates 500 QA pairs across 10 categories.

Usage:
    python build_benchmark.py                # Full pipeline: scrape + generate
    python build_benchmark.py --scrape-only  # Just scrape WikiVoyage
    python build_benchmark.py --generate-only # Generate QA from cached data
"""

import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()
    SSL_CONTEXT.check_hostname = False
    SSL_CONTEXT.verify_mode = ssl.CERT_NONE

TRAVELQA_DIR = Path(__file__).parent
SOURCES_DIR = TRAVELQA_DIR / "sources" / "wikivoyage"
BENCHMARK_FILE = TRAVELQA_DIR / "benchmark.json"

# WikiVoyage sections we need, mapped to our categories
SECTION_MAP = {
    "Stay safe": ["safety", "scams"],
    "Stay healthy": ["health"],
    "Respect": ["cultural_norms"],
    "Cope": ["emergency"],
    "Buy": ["currency"],
    "Connect": ["infrastructure"],
    "Talk": ["language"],
    "Get around": ["transportation"],
    "Get in": ["visa"],
}

CATEGORIES = [
    "safety", "health", "cultural_norms", "emergency", "currency",
    "infrastructure", "language", "transportation", "visa", "scams",
]

# 30+ countries across 6 continents
COUNTRIES = {
    # Asia
    "Japan": "Japan",
    "Thailand": "Thailand",
    "Vietnam": "Vietnam",
    "India": "India",
    "Indonesia": "Indonesia",
    "China": "China",
    "South Korea": "South_Korea",
    "Nepal": "Nepal",
    # Europe
    "France": "France",
    "Germany": "Germany",
    "Italy": "Italy",
    "Spain": "Spain",
    "Turkey": "Turkey",
    "Greece": "Greece",
    "Czech Republic": "Czech_Republic",
    "Norway": "Norway",
    # Americas
    "Mexico": "Mexico",
    "Colombia": "Colombia",
    "Brazil": "Brazil",
    "Peru": "Peru",
    "Argentina": "Argentina",
    "United States": "United_States_of_America",
    "Cuba": "Cuba",
    # Africa
    "Morocco": "Morocco",
    "Kenya": "Kenya",
    "South Africa": "South_Africa",
    "Egypt": "Egypt",
    "Tanzania": "Tanzania",
    # Oceania
    "Australia": "Australia",
    "New Zealand": "New_Zealand",
    # Middle East
    "United Arab Emirates": "United_Arab_Emirates",
    "Jordan": "Jordan",
}

RESERVE_COUNTRIES = {
    "Philippines": "Philippines",
    "Malaysia": "Malaysia",
    "Portugal": "Portugal",
    "Poland": "Poland",
    "Chile": "Chile",
}

# Factual ground truth data
EMERGENCY_NUMBERS = {
    "Japan": {"police": "110", "ambulance": "119", "fire": "119"},
    "Thailand": {"police": "191", "ambulance": "1669", "fire": "199"},
    "Vietnam": {"police": "113", "ambulance": "115", "fire": "114"},
    "India": {"police": "100", "ambulance": "108", "fire": "101", "universal": "112"},
    "Indonesia": {"police": "110", "ambulance": "118", "fire": "113"},
    "China": {"police": "110", "ambulance": "120", "fire": "119"},
    "South Korea": {"police": "112", "ambulance": "119", "fire": "119"},
    "Nepal": {"police": "100", "ambulance": "102", "fire": "101"},
    "France": {"universal": "112", "police": "17", "ambulance": "15", "fire": "18"},
    "Germany": {"universal": "112", "police": "110", "ambulance": "112", "fire": "112"},
    "Italy": {"universal": "112", "police": "113", "ambulance": "118", "fire": "115"},
    "Spain": {"universal": "112", "police": "091", "ambulance": "112", "fire": "112"},
    "Turkey": {"police": "155", "ambulance": "112", "fire": "110"},
    "Greece": {"universal": "112", "police": "100", "ambulance": "166", "fire": "199"},
    "Czech Republic": {"universal": "112", "police": "158", "ambulance": "155", "fire": "150"},
    "Norway": {"universal": "112", "police": "112", "ambulance": "113", "fire": "110"},
    "Mexico": {"universal": "911", "police": "911", "ambulance": "911", "fire": "911"},
    "Colombia": {"universal": "123", "police": "123", "ambulance": "123", "fire": "123"},
    "Brazil": {"police": "190", "ambulance": "192", "fire": "193"},
    "Peru": {"police": "105", "ambulance": "116", "fire": "116"},
    "Argentina": {"universal": "911", "police": "911", "ambulance": "107", "fire": "100"},
    "United States": {"universal": "911", "police": "911", "ambulance": "911", "fire": "911"},
    "Cuba": {"police": "106", "ambulance": "104", "fire": "105"},
    "Morocco": {"police": "19", "ambulance": "15", "fire": "15"},
    "Kenya": {"police": "999", "ambulance": "999", "fire": "999"},
    "South Africa": {"universal": "112", "police": "10111", "ambulance": "10177", "fire": "10177"},
    "Egypt": {"police": "122", "ambulance": "123", "fire": "180"},
    "Tanzania": {"police": "112", "ambulance": "114", "fire": "114"},
    "Australia": {"universal": "000", "police": "000", "ambulance": "000", "fire": "000"},
    "New Zealand": {"universal": "111", "police": "111", "ambulance": "111", "fire": "111"},
    "United Arab Emirates": {"police": "999", "ambulance": "998", "fire": "997"},
    "Jordan": {"police": "911", "ambulance": "911", "fire": "911"},
}

VOLTAGES = {
    "Japan": {"voltage": "100V", "frequency": "50/60Hz", "plug": "A, B"},
    "Thailand": {"voltage": "220V", "frequency": "50Hz", "plug": "A, B, C, O"},
    "Vietnam": {"voltage": "220V", "frequency": "50Hz", "plug": "A, C, G"},
    "India": {"voltage": "230V", "frequency": "50Hz", "plug": "C, D, M"},
    "Indonesia": {"voltage": "230V", "frequency": "50Hz", "plug": "C, F"},
    "China": {"voltage": "220V", "frequency": "50Hz", "plug": "A, C, I"},
    "South Korea": {"voltage": "220V", "frequency": "60Hz", "plug": "C, F"},
    "Nepal": {"voltage": "230V", "frequency": "50Hz", "plug": "C, D, M"},
    "France": {"voltage": "230V", "frequency": "50Hz", "plug": "C, E"},
    "Germany": {"voltage": "230V", "frequency": "50Hz", "plug": "C, F"},
    "Italy": {"voltage": "230V", "frequency": "50Hz", "plug": "C, F, L"},
    "Spain": {"voltage": "230V", "frequency": "50Hz", "plug": "C, F"},
    "Turkey": {"voltage": "230V", "frequency": "50Hz", "plug": "C, F"},
    "Greece": {"voltage": "230V", "frequency": "50Hz", "plug": "C, F"},
    "Czech Republic": {"voltage": "230V", "frequency": "50Hz", "plug": "C, E"},
    "Norway": {"voltage": "230V", "frequency": "50Hz", "plug": "C, F"},
    "Mexico": {"voltage": "127V", "frequency": "60Hz", "plug": "A, B"},
    "Colombia": {"voltage": "110V", "frequency": "60Hz", "plug": "A, B"},
    "Brazil": {"voltage": "127/220V", "frequency": "60Hz", "plug": "C, N"},
    "Peru": {"voltage": "220V", "frequency": "60Hz", "plug": "A, B, C"},
    "Argentina": {"voltage": "220V", "frequency": "50Hz", "plug": "C, I"},
    "United States": {"voltage": "120V", "frequency": "60Hz", "plug": "A, B"},
    "Cuba": {"voltage": "110/220V", "frequency": "60Hz", "plug": "A, B, C, L"},
    "Morocco": {"voltage": "220V", "frequency": "50Hz", "plug": "C, E"},
    "Kenya": {"voltage": "240V", "frequency": "50Hz", "plug": "G"},
    "South Africa": {"voltage": "230V", "frequency": "50Hz", "plug": "C, M, N"},
    "Egypt": {"voltage": "220V", "frequency": "50Hz", "plug": "C, F"},
    "Tanzania": {"voltage": "230V", "frequency": "50Hz", "plug": "D, G"},
    "Australia": {"voltage": "230V", "frequency": "50Hz", "plug": "I"},
    "New Zealand": {"voltage": "230V", "frequency": "50Hz", "plug": "I"},
    "United Arab Emirates": {"voltage": "220V", "frequency": "50Hz", "plug": "C, D, G"},
    "Jordan": {"voltage": "230V", "frequency": "50Hz", "plug": "B, C, D, F, G, J"},
}

CURRENCIES = {
    "Japan": {"currency": "Japanese Yen", "code": "JPY", "symbol": "\u00a5"},
    "Thailand": {"currency": "Thai Baht", "code": "THB", "symbol": "\u0e3f"},
    "Vietnam": {"currency": "Vietnamese Dong", "code": "VND", "symbol": "\u20ab"},
    "India": {"currency": "Indian Rupee", "code": "INR", "symbol": "\u20b9"},
    "Indonesia": {"currency": "Indonesian Rupiah", "code": "IDR", "symbol": "Rp"},
    "China": {"currency": "Chinese Yuan", "code": "CNY", "symbol": "\u00a5"},
    "South Korea": {"currency": "South Korean Won", "code": "KRW", "symbol": "\u20a9"},
    "Nepal": {"currency": "Nepalese Rupee", "code": "NPR", "symbol": "Rs"},
    "France": {"currency": "Euro", "code": "EUR", "symbol": "\u20ac"},
    "Germany": {"currency": "Euro", "code": "EUR", "symbol": "\u20ac"},
    "Italy": {"currency": "Euro", "code": "EUR", "symbol": "\u20ac"},
    "Spain": {"currency": "Euro", "code": "EUR", "symbol": "\u20ac"},
    "Turkey": {"currency": "Turkish Lira", "code": "TRY", "symbol": "\u20ba"},
    "Greece": {"currency": "Euro", "code": "EUR", "symbol": "\u20ac"},
    "Czech Republic": {"currency": "Czech Koruna", "code": "CZK", "symbol": "K\u010d"},
    "Norway": {"currency": "Norwegian Krone", "code": "NOK", "symbol": "kr"},
    "Mexico": {"currency": "Mexican Peso", "code": "MXN", "symbol": "$"},
    "Colombia": {"currency": "Colombian Peso", "code": "COP", "symbol": "$"},
    "Brazil": {"currency": "Brazilian Real", "code": "BRL", "symbol": "R$"},
    "Peru": {"currency": "Peruvian Sol", "code": "PEN", "symbol": "S/."},
    "Argentina": {"currency": "Argentine Peso", "code": "ARS", "symbol": "$"},
    "United States": {"currency": "US Dollar", "code": "USD", "symbol": "$"},
    "Cuba": {"currency": "Cuban Peso", "code": "CUP", "symbol": "$"},
    "Morocco": {"currency": "Moroccan Dirham", "code": "MAD", "symbol": "MAD"},
    "Kenya": {"currency": "Kenyan Shilling", "code": "KES", "symbol": "KSh"},
    "South Africa": {"currency": "South African Rand", "code": "ZAR", "symbol": "R"},
    "Egypt": {"currency": "Egyptian Pound", "code": "EGP", "symbol": "E\u00a3"},
    "Tanzania": {"currency": "Tanzanian Shilling", "code": "TZS", "symbol": "TSh"},
    "Australia": {"currency": "Australian Dollar", "code": "AUD", "symbol": "A$"},
    "New Zealand": {"currency": "New Zealand Dollar", "code": "NZD", "symbol": "NZ$"},
    "United Arab Emirates": {"currency": "UAE Dirham", "code": "AED", "symbol": "AED"},
    "Jordan": {"currency": "Jordanian Dinar", "code": "JOD", "symbol": "JD"},
}

DRIVING_SIDES = {
    "Japan": "left", "Thailand": "left", "Vietnam": "right", "India": "left",
    "Indonesia": "left", "China": "right", "South Korea": "right", "Nepal": "left",
    "France": "right", "Germany": "right", "Italy": "right", "Spain": "right",
    "Turkey": "right", "Greece": "right", "Czech Republic": "right", "Norway": "right",
    "Mexico": "right", "Colombia": "right", "Brazil": "right", "Peru": "right",
    "Argentina": "right", "United States": "right", "Cuba": "right",
    "Morocco": "right", "Kenya": "left", "South Africa": "left", "Egypt": "right",
    "Tanzania": "left", "Australia": "left", "New Zealand": "left",
    "United Arab Emirates": "right", "Jordan": "right",
}


def fetch_wikivoyage(country_slug: str) -> dict | None:
    """Fetch WikiVoyage page via MediaWiki API, return parsed sections."""
    url = (
        f"https://en.wikivoyage.org/w/api.php?"
        f"action=parse&page={urllib.parse.quote(country_slug)}"
        f"&prop=wikitext&format=json"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TravelQA-Benchmark/1.0"})
        with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as resp:
            data = json.loads(resp.read().decode())
        if "parse" not in data:
            return None
        return data["parse"]
    except Exception as e:
        print(f"  Error fetching {country_slug}: {e}")
        return None


def parse_sections(wikitext: str) -> dict[str, str]:
    """Parse MediaWiki wikitext into named sections."""
    sections = {}
    current_section = "Introduction"
    current_text = []

    for line in wikitext.split("\n"):
        # Match == Section == or === Subsection ===
        match = re.match(r'^(={2,3})\s*(.+?)\s*\1\s*$', line)
        if match:
            # Save previous section
            text = "\n".join(current_text).strip()
            if text:
                sections[current_section] = text
            current_section = match.group(2).strip()
            current_text = []
        else:
            current_text.append(line)

    # Save last section
    text = "\n".join(current_text).strip()
    if text:
        sections[current_section] = text

    return sections


def clean_wikitext(text: str) -> str:
    """Remove wiki markup, keeping readable text."""
    # Remove templates like {{...}}
    text = re.sub(r'\{\{[^}]*\}\}', '', text)
    # Convert [[link|display]] to display, [[link]] to link
    text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', text)
    # Remove external links [http://... display] -> display
    text = re.sub(r'\[https?://\S+\s+([^\]]+)\]', r'\1', text)
    text = re.sub(r'\[https?://\S+\]', '', text)
    # Remove bold/italic markup
    text = re.sub(r"'{2,3}", '', text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove category links
    text = re.sub(r'\[\[Category:[^\]]+\]\]', '', text)
    # Collapse whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def scrape_country(country_name: str, country_slug: str) -> dict | None:
    """Scrape a single country's WikiVoyage page."""
    cache_file = SOURCES_DIR / f"{country_name.lower().replace(' ', '_')}.json"

    # Check cache (< 30 days old)
    if cache_file.exists():
        import os
        age_days = (time.time() - os.path.getmtime(cache_file)) / 86400
        if age_days < 30:
            print(f"  [cached] {country_name}")
            with open(cache_file) as f:
                return json.load(f)

    print(f"  Fetching {country_name} ({country_slug})...")
    parsed = fetch_wikivoyage(country_slug)
    if not parsed:
        return None

    wikitext = parsed.get("wikitext", {}).get("*", "")
    if not wikitext:
        return None

    raw_sections = parse_sections(wikitext)
    cleaned = {}
    for section_name, section_text in raw_sections.items():
        cleaned_text = clean_wikitext(section_text)
        if len(cleaned_text) > 50:  # Skip trivially short sections
            cleaned[section_name] = cleaned_text

    result = {
        "country": country_name,
        "slug": country_slug,
        "scraped_at": datetime.now().isoformat(),
        "sections": cleaned,
        "section_count": len(cleaned),
    }

    # Save to cache
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return result


def check_country_coverage(data: dict) -> tuple[bool, list[str]]:
    """Check if country has enough WikiVoyage content. Returns (pass, missing_sections)."""
    sections = data.get("sections", {})

    # Need at least 3 substantial sections (>100 words)
    substantial = sum(1 for s in sections.values() if len(s.split()) > 100)
    passes = substantial >= 3
    missing = [] if passes else ["need 3+ substantial sections"]
    return passes, missing


def scrape_all_countries() -> dict[str, dict]:
    """Scrape WikiVoyage for all target countries."""
    print("=== Scraping WikiVoyage ===\n")
    scraped = {}
    failed = []

    for country_name, slug in COUNTRIES.items():
        data = scrape_country(country_name, slug)
        if data:
            passes, missing = check_country_coverage(data)
            if passes:
                scraped[country_name] = data
                section_count = data["section_count"]
                print(f"    OK: {section_count} sections")
            else:
                print(f"    THIN: missing {missing} — will try reserve")
                failed.append(country_name)
        else:
            print(f"    FAILED: no data")
            failed.append(country_name)
        time.sleep(0.5)  # Rate limit

    # Try reserve countries for any failures
    if failed:
        print(f"\n  Trying {len(failed)} reserve countries...")
        for country_name, slug in RESERVE_COUNTRIES.items():
            if not failed:
                break
            data = scrape_country(country_name, slug)
            if data:
                passes, _ = check_country_coverage(data)
                if passes:
                    scraped[country_name] = data
                    failed.pop(0)  # Replace one failed country
                    print(f"    Substituted {country_name}")
            time.sleep(0.5)

    print(f"\n  Total countries scraped: {len(scraped)}")
    if failed:
        print(f"  Failed: {failed}")

    return scraped


# Aliases: map target section names to alternate names found in WikiVoyage
SECTION_ALIASES = {
    "stay safe": ["stay safe", "safety", "crime", "police", "danger", "scam"],
    "stay healthy": ["stay healthy", "health", "medical", "hospital", "disease", "water"],
    "respect": ["respect", "culture", "customs", "etiquette", "cultural diversity", "people and customs", "people"],
    "cope": ["cope", "emergency", "embass", "consulate"],
    "buy": ["buy", "shopping", "money", "currency", "cost", "bargain"],
    "connect": ["connect", "electricity", "internet", "phone", "mobile", "wi-fi", "wifi", "power"],
    "talk": ["talk", "language", "phrasebook"],
    "get around": ["get around", "by bus", "by train", "by car", "by plane", "transport", "by taxi", "driving"],
    "get in": ["get in", "visa", "entry", "passport", "border", "customs"],
}


def get_section_text(country_data: dict, target_section: str) -> str:
    """Find a section by flexible name matching with aliases."""
    sections = country_data.get("sections", {})
    target_lower = target_section.lower()

    # Direct match first
    for name, text in sections.items():
        if target_lower in name.lower():
            return text

    # Try aliases
    aliases = SECTION_ALIASES.get(target_lower, [])
    matched_texts = []
    for name, text in sections.items():
        name_lower = name.lower().strip("= ")
        for alias in aliases:
            if alias in name_lower:
                matched_texts.append(text)
                break

    # Concatenate all matching sections
    return "\n\n".join(matched_texts)


def generate_safety_questions(country: str, section_text: str) -> list[dict]:
    """Generate safety-category questions from WikiVoyage Stay Safe section."""
    questions = []

    # Extract safety-relevant sentences
    sentences = [s.strip() for s in re.split(r'[.!]', section_text) if len(s.strip()) > 30]

    # Template: area safety
    if any(w in section_text.lower() for w in ["pickpocket", "theft", "steal", "robbery"]):
        questions.append({
            "category": "safety",
            "country": country,
            "question": f"What is a common safety concern for tourists in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Pickpocketing and petty theft",
                "Volcanic eruptions",
                "Extreme cold weather",
                "Radioactive contamination"
            ],
            "correct_choice": "A",
            "difficulty": "easy",
        })

    # Template: night safety
    if any(w in section_text.lower() for w in ["night", "dark", "evening", "after dark"]):
        questions.append({
            "category": "safety",
            "country": country,
            "question": f"What safety precaution is recommended when traveling at night in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Avoid walking alone in poorly lit areas",
                "Always carry a flashlight and whistle",
                "Wear reflective clothing at all times",
                "Travel only by helicopter after sunset"
            ],
            "correct_choice": "A",
            "difficulty": "medium",
        })

    # Template: scam awareness
    if any(w in section_text.lower() for w in ["scam", "fraud", "trick", "overcharg", "tout"]):
        questions.append({
            "category": "safety",
            "country": country,
            "question": f"Which of the following is a known risk for tourists in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Tourist-targeted scams and overcharging",
                "Mandatory military service for visitors",
                "Spontaneous building collapses",
                "Government surveillance of all tourists"
            ],
            "correct_choice": "A",
            "difficulty": "easy",
        })

    # Template: natural hazards
    if any(w in section_text.lower() for w in ["earthquake", "typhoon", "flood", "tsunami", "hurricane", "monsoon", "cyclone"]):
        hazard = "natural disasters"
        for h in ["earthquake", "typhoon", "flood", "tsunami", "hurricane", "monsoon", "cyclone"]:
            if h in section_text.lower():
                hazard = f"{h}s"
                break
        questions.append({
            "category": "safety",
            "country": country,
            "question": f"What natural hazard should travelers to {country} be aware of?",
            "answer_type": "multiple_choice",
            "choices": [
                hazard.capitalize(),
                "Meteorite impacts",
                "Permanent ice storms",
                "Quicksand in urban areas"
            ],
            "correct_choice": "A",
            "difficulty": "medium",
        })

    # Template: women's safety
    if any(w in section_text.lower() for w in ["women", "female", "harassment", "gender"]):
        questions.append({
            "category": "safety",
            "country": country,
            "question": f"What specific safety advice exists for women travelers in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Be cautious in isolated areas and use reputable transportation",
                "Women are not allowed to travel solo",
                "All hotels have mandatory women-only floors",
                "Female tourists must register with the local police daily"
            ],
            "correct_choice": "A",
            "difficulty": "medium",
        })

    # Fallback: general travel safety (always generate at least 1)
    if not questions:
        questions.append({
            "category": "safety",
            "country": country,
            "question": f"What is the most important general safety advice for tourists visiting {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Stay aware of your surroundings and keep valuables secure",
                "There are no safety concerns whatsoever",
                "Tourists are immune from local laws",
                "Safety is only a concern in rural areas"
            ],
            "correct_choice": "A",
            "difficulty": "easy",
        })

    return questions


def generate_health_questions(country: str, section_text: str) -> list[dict]:
    """Generate health-category questions from Stay Healthy section."""
    questions = []

    if any(w in section_text.lower() for w in ["water", "tap water", "bottled water", "drink"]):
        safe = "safe" if any(w in section_text.lower() for w in ["tap water is safe", "safe to drink", "potable"]) else "not safe"
        if safe == "not safe":
            questions.append({
                "category": "health",
                "country": country,
                "question": f"Is tap water generally safe to drink in {country}?",
                "answer_type": "multiple_choice",
                "choices": [
                    "No, drink bottled or purified water",
                    "Yes, tap water is safe everywhere",
                    "Only in the capital city",
                    "Only during winter months"
                ],
                "correct_choice": "A",
                "difficulty": "easy",
            })
        else:
            questions.append({
                "category": "health",
                "country": country,
                "question": f"Is tap water generally safe to drink in {country}?",
                "answer_type": "multiple_choice",
                "choices": [
                    "Yes, tap water is generally safe",
                    "No, always drink bottled water",
                    "Only in hotels",
                    "Only after boiling for 20 minutes"
                ],
                "correct_choice": "A",
                "difficulty": "easy",
            })

    if any(w in section_text.lower() for w in ["malaria", "dengue", "mosquito", "insect"]):
        questions.append({
            "category": "health",
            "country": country,
            "question": f"What mosquito-borne disease risk exists in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Malaria and/or dengue fever are risks in some areas",
                "No mosquito-borne disease risk exists",
                "Only malaria, and only in cities",
                "Mosquitoes in this country do not carry diseases"
            ],
            "correct_choice": "A",
            "difficulty": "medium",
        })

    if any(w in section_text.lower() for w in ["vaccine", "vaccination", "immuniz"]):
        questions.append({
            "category": "health",
            "country": country,
            "question": f"What should travelers know about vaccinations for {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Check recommended vaccinations before traveling",
                "No vaccinations are needed for any traveler",
                "Vaccinations are given free at the airport on arrival",
                "Only COVID vaccination is relevant"
            ],
            "correct_choice": "A",
            "difficulty": "easy",
        })

    if any(w in section_text.lower() for w in ["hospital", "clinic", "medical", "doctor", "pharmacy"]):
        questions.append({
            "category": "health",
            "country": country,
            "question": f"What is the general state of healthcare access for tourists in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Medical facilities are available but quality varies by region",
                "Healthcare is completely free for all tourists",
                "No medical facilities exist outside the capital",
                "Tourists are not permitted to use local hospitals"
            ],
            "correct_choice": "A",
            "difficulty": "medium",
        })

    if any(w in section_text.lower() for w in ["altitude", "mountain", "elevation"]):
        questions.append({
            "category": "health",
            "country": country,
            "question": f"What health risk should travelers to high-altitude areas of {country} consider?",
            "answer_type": "multiple_choice",
            "choices": [
                "Altitude sickness — acclimatize gradually",
                "High altitude causes permanent hearing loss",
                "UV radiation is lower at high altitude",
                "Altitude has no health effects on travelers"
            ],
            "correct_choice": "A",
            "difficulty": "medium",
        })

    return questions


def generate_cultural_questions(country: str, section_text: str) -> list[dict]:
    """Generate cultural norms questions from Respect section."""
    questions = []

    if any(w in section_text.lower() for w in ["shoe", "shoes", "footwear"]):
        questions.append({
            "category": "cultural_norms",
            "country": country,
            "question": f"What is a common cultural etiquette rule about footwear in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Remove shoes before entering homes and some sacred places",
                "Always wear closed-toe shoes in public",
                "Sandals are considered formal footwear",
                "Shoes must be purchased locally"
            ],
            "correct_choice": "A",
            "difficulty": "easy",
        })

    if any(w in section_text.lower() for w in ["tip", "tipping", "gratuity"]):
        questions.append({
            "category": "cultural_norms",
            "country": country,
            "question": f"What is the tipping culture like in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Tipping customs vary — check local expectations",
                "Tipping is illegal",
                "A 50% tip is always expected",
                "Tips must be given in US dollars only"
            ],
            "correct_choice": "A",
            "difficulty": "medium",
        })

    if any(w in section_text.lower() for w in ["dress", "clothing", "modest", "cover"]):
        questions.append({
            "category": "cultural_norms",
            "country": country,
            "question": f"What dress code expectations should tourists be aware of in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Dress modestly when visiting religious or traditional sites",
                "There are no dress expectations of any kind",
                "Western casual clothing is mandatory",
                "Tourists must wear traditional local clothing"
            ],
            "correct_choice": "A",
            "difficulty": "easy",
        })

    if any(w in section_text.lower() for w in ["photo", "photograph", "camera", "picture"]):
        questions.append({
            "category": "cultural_norms",
            "country": country,
            "question": f"What should travelers know about photography etiquette in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Ask permission before photographing people and respect restricted areas",
                "Photography is unrestricted everywhere",
                "All photographs require a government permit",
                "Only film cameras are allowed, not digital"
            ],
            "correct_choice": "A",
            "difficulty": "easy",
        })

    if any(w in section_text.lower() for w in ["religion", "temple", "mosque", "church", "sacred", "holy"]):
        questions.append({
            "category": "cultural_norms",
            "country": country,
            "question": f"What should tourists know about religious site etiquette in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Show respect: dress modestly, follow local customs, and be quiet",
                "Religious sites are open-air museums with no rules",
                "Tourists are generally not allowed in religious sites",
                "You must make a donation to enter any religious site"
            ],
            "correct_choice": "A",
            "difficulty": "easy",
        })

    # Fallback: general cultural awareness
    if not questions:
        questions.append({
            "category": "cultural_norms",
            "country": country,
            "question": f"What is the most important cultural etiquette advice for visitors to {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Learn and respect local customs, greetings, and social norms",
                "Western customs are universally accepted",
                "Cultural awareness is unnecessary for tourists",
                "Locals expect tourists to behave exactly as they would at home"
            ],
            "correct_choice": "A",
            "difficulty": "easy",
        })

    return questions


def generate_emergency_questions(country: str) -> list[dict]:
    """Generate emergency number questions from factual data."""
    questions = []
    numbers = EMERGENCY_NUMBERS.get(country, {})
    if not numbers:
        return []

    # Police number
    if "police" in numbers:
        questions.append({
            "category": "emergency",
            "country": country,
            "question": f"What is the emergency number for police in {country}?",
            "answer": numbers["police"],
            "answer_type": "exact_match",
            "difficulty": "easy",
        })

    # Ambulance number
    if "ambulance" in numbers:
        questions.append({
            "category": "emergency",
            "country": country,
            "question": f"What is the emergency number for medical/ambulance services in {country}?",
            "answer": numbers["ambulance"],
            "answer_type": "exact_match",
            "difficulty": "easy",
        })

    # Universal number
    if "universal" in numbers:
        questions.append({
            "category": "emergency",
            "country": country,
            "question": f"What is the universal emergency number in {country}?",
            "answer": numbers["universal"],
            "answer_type": "exact_match",
            "difficulty": "easy",
        })

    # MC: which is correct
    if "police" in numbers:
        wrong = ["555", "999", "123", "411", "311", "100", "110", "112", "911", "000", "119"]
        correct = numbers["police"]
        distractors = [n for n in wrong if n != correct][:3]
        choices = [correct] + distractors
        # Shuffle deterministically
        import hashlib
        seed = int(hashlib.md5(f"{country}-emergency-mc".encode()).hexdigest()[:8], 16)
        rng = __import__("random").Random(seed)
        rng.shuffle(choices)
        correct_idx = choices.index(correct)
        correct_letter = chr(65 + correct_idx)

        questions.append({
            "category": "emergency",
            "country": country,
            "question": f"Which of the following is the correct police emergency number in {country}?",
            "answer_type": "multiple_choice",
            "choices": choices,
            "correct_choice": correct_letter,
            "difficulty": "medium",
        })

    return questions


def generate_currency_questions(country: str, section_text: str) -> list[dict]:
    """Generate currency questions from Buy section + factual data."""
    questions = []
    curr = CURRENCIES.get(country, {})
    if not curr:
        return []

    # Currency name
    questions.append({
        "category": "currency",
        "country": country,
        "question": f"What is the official currency of {country}?",
        "answer": curr["currency"],
        "answer_type": "exact_match",
        "difficulty": "easy",
    })

    # Currency code
    questions.append({
        "category": "currency",
        "country": country,
        "question": f"What is the ISO currency code for {country}'s currency?",
        "answer": curr["code"],
        "answer_type": "exact_match",
        "difficulty": "easy",
    })

    # MC version
    wrong_codes = ["USD", "EUR", "GBP", "JPY", "CNY", "AUD", "BRL", "INR", "KRW", "THB", "VND", "MXN"]
    correct_code = curr["code"]
    distractors = [c for c in wrong_codes if c != correct_code][:3]
    choices_codes = [correct_code] + distractors

    import hashlib
    seed = int(hashlib.md5(f"{country}-currency-mc".encode()).hexdigest()[:8], 16)
    rng = __import__("random").Random(seed)
    rng.shuffle(choices_codes)
    correct_idx = choices_codes.index(correct_code)

    questions.append({
        "category": "currency",
        "country": country,
        "question": f"Which currency code is used in {country}?",
        "answer_type": "multiple_choice",
        "choices": choices_codes,
        "correct_choice": chr(65 + correct_idx),
        "difficulty": "easy",
    })

    # ATM/card usage from section text
    if any(w in section_text.lower() for w in ["atm", "credit card", "cash", "money exchange"]):
        questions.append({
            "category": "currency",
            "country": country,
            "question": f"What should travelers know about using money in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Carry some local cash; card acceptance varies by area",
                "Only cryptocurrency is accepted",
                "Credit cards are accepted absolutely everywhere",
                "Foreign currency is widely accepted instead of local currency"
            ],
            "correct_choice": "A",
            "difficulty": "medium",
        })

    return questions


def generate_infrastructure_questions(country: str, section_text: str) -> list[dict]:
    """Generate infrastructure questions from Connect section + factual data."""
    questions = []
    volt = VOLTAGES.get(country, {})

    if volt:
        # Voltage question
        questions.append({
            "category": "infrastructure",
            "country": country,
            "question": f"What is the standard electrical voltage in {country}?",
            "answer": volt["voltage"],
            "answer_type": "exact_match",
            "difficulty": "easy",
        })

        # Plug type MC
        questions.append({
            "category": "infrastructure",
            "country": country,
            "question": f"What type of electrical plug is used in {country}?",
            "answer": f"Type {volt['plug']}",
            "answer_type": "exact_match",
            "difficulty": "medium",
        })

    # Internet/connectivity from section text
    if any(w in section_text.lower() for w in ["wifi", "wi-fi", "internet", "sim", "mobile"]):
        questions.append({
            "category": "infrastructure",
            "country": country,
            "question": f"How can travelers get internet access in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Buy a local SIM card or use available Wi-Fi hotspots",
                "Internet is not available for tourists",
                "Only satellite internet works in this country",
                "Internet requires a government license for tourists"
            ],
            "correct_choice": "A",
            "difficulty": "easy",
        })

    return questions


def generate_language_questions(country: str, section_text: str) -> list[dict]:
    """Generate language/phrase questions from Talk section."""
    questions = []

    # Extract key phrases — look for patterns like "word" - meaning
    phrase_patterns = re.findall(
        r'["\u201c]([^"\u201d]{1,30})["\u201d]\s*[-\u2013\u2014=:]\s*([^.\n]{3,60})',
        section_text
    )

    if phrase_patterns:
        for phrase, meaning in phrase_patterns[:2]:
            questions.append({
                "category": "language",
                "country": country,
                "question": f'In {country}, what does the local phrase "{phrase.strip()}" mean?',
                "answer": meaning.strip(),
                "answer_type": "keyword_match",
                "keywords": [w.lower() for w in meaning.strip().split() if len(w) > 3],
                "difficulty": "hard",
            })

    # General language question
    languages = {
        "Japan": "Japanese", "Thailand": "Thai", "Vietnam": "Vietnamese",
        "India": "Hindi and English", "Indonesia": "Indonesian (Bahasa Indonesia)",
        "China": "Mandarin Chinese", "South Korea": "Korean", "Nepal": "Nepali",
        "France": "French", "Germany": "German", "Italy": "Italian",
        "Spain": "Spanish", "Turkey": "Turkish", "Greece": "Greek",
        "Czech Republic": "Czech", "Norway": "Norwegian",
        "Mexico": "Spanish", "Colombia": "Spanish", "Brazil": "Portuguese",
        "Peru": "Spanish", "Argentina": "Spanish", "United States": "English",
        "Cuba": "Spanish", "Morocco": "Arabic and French", "Kenya": "Swahili and English",
        "South Africa": "English, Afrikaans, Zulu, and others",
        "Egypt": "Arabic", "Tanzania": "Swahili and English",
        "Australia": "English", "New Zealand": "English and Maori",
        "United Arab Emirates": "Arabic", "Jordan": "Arabic",
        "Philippines": "Filipino and English", "Malaysia": "Malay",
        "Portugal": "Portuguese", "Poland": "Polish", "Chile": "Spanish",
    }

    lang = languages.get(country, "")
    if lang:
        questions.append({
            "category": "language",
            "country": country,
            "question": f"What is the primary official language of {country}?",
            "answer": lang,
            "answer_type": "keyword_match",
            "keywords": [w.lower() for w in lang.split() if len(w) > 2 and w.lower() != "and"],
            "difficulty": "easy",
        })

    # Useful phrases
    greetings = {
        "Japan": ("Konnichiwa", "Hello"),
        "Thailand": ("Sawasdee", "Hello"),
        "France": ("Bonjour", "Hello/Good day"),
        "Germany": ("Guten Tag", "Good day"),
        "Italy": ("Buongiorno", "Good morning/day"),
        "Spain": ("Hola", "Hello"),
        "Brazil": ("Ola", "Hello"),
        "China": ("Ni hao", "Hello"),
        "South Korea": ("Annyeonghaseyo", "Hello"),
        "Vietnam": ("Xin chao", "Hello"),
        "Turkey": ("Merhaba", "Hello"),
        "Greece": ("Yassas", "Hello"),
        "Morocco": ("Salam", "Peace/Hello"),
        "Egypt": ("Ahlan", "Hello"),
        "Indonesia": ("Selamat", "Greetings"),
        "India": ("Namaste", "Hello"),
    }

    if country in greetings:
        word, meaning = greetings[country]
        questions.append({
            "category": "language",
            "country": country,
            "question": f'What does "{word}" mean in {country}?',
            "answer": meaning,
            "answer_type": "keyword_match",
            "keywords": [meaning.lower().split("/")[0].strip()],
            "difficulty": "easy",
        })

    # "Thank you" phrases
    thanks = {
        "Japan": ("Arigatou", "Thank you"),
        "Thailand": ("Khop khun", "Thank you"),
        "France": ("Merci", "Thank you"),
        "Germany": ("Danke", "Thank you"),
        "Italy": ("Grazie", "Thank you"),
        "Spain": ("Gracias", "Thank you"),
        "Brazil": ("Obrigado", "Thank you"),
        "China": ("Xie xie", "Thank you"),
        "South Korea": ("Gamsahamnida", "Thank you"),
        "Vietnam": ("Cam on", "Thank you"),
        "Turkey": ("Tesekkur ederim", "Thank you"),
        "Greece": ("Efharisto", "Thank you"),
        "Morocco": ("Shukran", "Thank you"),
        "Egypt": ("Shukran", "Thank you"),
        "Indonesia": ("Terima kasih", "Thank you"),
        "India": ("Dhanyavaad", "Thank you"),
        "Peru": ("Gracias", "Thank you"),
        "Colombia": ("Gracias", "Thank you"),
        "Cuba": ("Gracias", "Thank you"),
        "Mexico": ("Gracias", "Thank you"),
        "Argentina": ("Gracias", "Thank you"),
        "Nepal": ("Dhanyabad", "Thank you"),
        "Philippines": ("Salamat", "Thank you"),
        "Malaysia": ("Terima kasih", "Thank you"),
        "Kenya": ("Asante", "Thank you"),
        "Tanzania": ("Asante", "Thank you"),
        "South Africa": ("Dankie", "Thank you (Afrikaans)"),
        "Jordan": ("Shukran", "Thank you"),
        "United Arab Emirates": ("Shukran", "Thank you"),
        "Norway": ("Takk", "Thank you"),
        "Czech Republic": ("Dekuji", "Thank you"),
    }

    if country in thanks:
        word, meaning = thanks[country]
        questions.append({
            "category": "language",
            "country": country,
            "question": f'How do you say "thank you" in the local language of {country}?',
            "answer": word,
            "answer_type": "keyword_match",
            "keywords": [word.lower().split()[0]],
            "difficulty": "easy",
        })

    return questions


def generate_transportation_questions(country: str, section_text: str) -> list[dict]:
    """Generate transportation questions from Get Around section."""
    questions = []

    # Driving side
    side = DRIVING_SIDES.get(country)
    if side:
        questions.append({
            "category": "transportation",
            "country": country,
            "question": f"Which side of the road do people drive on in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                f"The {side} side",
                f"The {'right' if side == 'left' else 'left'} side",
                "Either side is acceptable",
                "There are no road driving rules"
            ],
            "correct_choice": "A",
            "difficulty": "easy",
        })

    # Public transport
    if any(w in section_text.lower() for w in ["train", "railway", "rail"]):
        questions.append({
            "category": "transportation",
            "country": country,
            "question": f"What is a common mode of long-distance transportation in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Train/railway network",
                "Camel caravans",
                "Zip lines between cities",
                "Underground tunnels for walking"
            ],
            "correct_choice": "A",
            "difficulty": "easy",
        })

    if any(w in section_text.lower() for w in ["bus", "minibus", "coach"]):
        questions.append({
            "category": "transportation",
            "country": country,
            "question": f"What bus/coach travel advice applies to {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Buses are widely available; quality and safety vary",
                "There are no bus services",
                "All buses are luxury coaches with WiFi",
                "Bus travel is restricted to citizens only"
            ],
            "correct_choice": "A",
            "difficulty": "medium",
        })

    if any(w in section_text.lower() for w in ["taxi", "ride", "uber", "grab", "lyft"]):
        questions.append({
            "category": "transportation",
            "country": country,
            "question": f"What should travelers know about taxis in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Use metered taxis or ride-hailing apps; agree on fare beforehand if unmetered",
                "Taxis are free for tourists",
                "Only hotel taxis are legal for tourists",
                "Taxis do not exist in this country"
            ],
            "correct_choice": "A",
            "difficulty": "medium",
        })

    if any(w in section_text.lower() for w in ["domestic flight", "fly", "airline", "airport"]):
        questions.append({
            "category": "transportation",
            "country": country,
            "question": f"Is domestic air travel a viable option in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Yes, domestic flights connect major cities",
                "No, only international flights exist",
                "Air travel is banned for tourists",
                "Only military aircraft are available"
            ],
            "correct_choice": "A",
            "difficulty": "easy",
        })

    return questions


def generate_visa_questions(country: str, section_text: str) -> list[dict]:
    """Generate visa/entry questions from Get In section."""
    questions = []

    if any(w in section_text.lower() for w in ["visa", "visa-free", "visa on arrival", "e-visa"]):
        questions.append({
            "category": "visa",
            "country": country,
            "question": f"What should travelers research before visiting {country} regarding entry requirements?",
            "answer_type": "multiple_choice",
            "choices": [
                "Visa requirements vary by nationality — check before traveling",
                "No visa is ever required for any nationality",
                "All visitors must obtain a visa that takes 6 months to process",
                "Visas can only be obtained at the border with cash"
            ],
            "correct_choice": "A",
            "difficulty": "easy",
        })

    if any(w in section_text.lower() for w in ["passport", "valid", "expir"]):
        questions.append({
            "category": "visa",
            "country": country,
            "question": f"What passport validity is typically required to enter {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "At least 6 months validity beyond your planned stay",
                "Any passport with at least 1 day validity",
                "Passports are not required for entry",
                "Exactly 10 years validity is mandatory"
            ],
            "correct_choice": "A",
            "difficulty": "easy",
        })

    if any(w in section_text.lower() for w in ["custom", "declaration", "import", "prohibited", "drug"]):
        questions.append({
            "category": "visa",
            "country": country,
            "question": f"What should travelers know about customs regulations in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Declare required items and be aware of prohibited goods",
                "There are no customs checks for tourists",
                "All personal items must be declared and taxed",
                "Customs checks only apply to commercial goods"
            ],
            "correct_choice": "A",
            "difficulty": "medium",
        })

    return questions


def generate_scam_questions(country: str, section_text: str) -> list[dict]:
    """Generate scam/pitfall questions from Stay Safe section."""
    questions = []

    if any(w in section_text.lower() for w in ["scam", "con", "trick", "fraud"]):
        questions.append({
            "category": "scams",
            "country": country,
            "question": f"What type of scam should tourists watch out for in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Tourist-targeted scams involving inflated prices or fake services",
                "Government-run scams at the airport",
                "Scams do not exist in this country",
                "Only online scams, never in person"
            ],
            "correct_choice": "A",
            "difficulty": "easy",
        })

    if any(w in section_text.lower() for w in ["overcharg", "price", "bargain", "haggl", "negoti"]):
        questions.append({
            "category": "scams",
            "country": country,
            "question": f"What pricing advice should tourists follow in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Be aware of tourist pricing — negotiate where customary and know fair prices",
                "All prices are fixed by law and never inflated",
                "Always pay the first price quoted without question",
                "Bargaining is considered extremely rude everywhere"
            ],
            "correct_choice": "A",
            "difficulty": "medium",
        })

    if any(w in section_text.lower() for w in ["taxi scam", "meter", "overcharg"]):
        questions.append({
            "category": "scams",
            "country": country,
            "question": f"How can tourists avoid taxi-related scams in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Insist on using the meter or agree on the fare before departing",
                "Taxis are government-regulated and scam-free",
                "Always pay triple the meter fare as a courtesy",
                "Only use taxis with no license plates"
            ],
            "correct_choice": "A",
            "difficulty": "easy",
        })

    if any(w in section_text.lower() for w in ["fake", "counterfeit", "knock-off"]):
        questions.append({
            "category": "scams",
            "country": country,
            "question": f"What should tourists know about counterfeit goods in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Counterfeit goods are common; buying them may be illegal",
                "All goods sold to tourists are guaranteed authentic",
                "Counterfeit goods are legal and encouraged",
                "Only electronics are counterfeited, not clothing"
            ],
            "correct_choice": "A",
            "difficulty": "medium",
        })

    # Fallback: general scam awareness (always at least 2)
    if len(questions) < 2:
        questions.append({
            "category": "scams",
            "country": country,
            "question": f"What general scam awareness advice applies to tourists in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Be cautious of unsolicited offers, verify prices, and use official services",
                "Scams never target tourists in this country",
                "Only locals get scammed, never foreigners",
                "The government guarantees all tourist transactions"
            ],
            "correct_choice": "A",
            "difficulty": "easy",
        })
    if len(questions) < 2:
        questions.append({
            "category": "scams",
            "country": country,
            "question": f"What should a tourist do if they suspect they are being scammed in {country}?",
            "answer_type": "multiple_choice",
            "choices": [
                "Walk away calmly and report to local authorities or your embassy",
                "Argue loudly to attract attention",
                "Pay whatever is demanded to avoid conflict",
                "Scams are impossible to avoid so don't worry"
            ],
            "correct_choice": "A",
            "difficulty": "medium",
        })

    return questions


def generate_all_questions(scraped_data: dict[str, dict]) -> list[dict]:
    """Generate QA pairs for all countries and categories."""
    all_questions = []
    category_counts = {c: 0 for c in CATEGORIES}
    target_per_category = 50

    for country, data in scraped_data.items():
        sections = data.get("sections", {})

        # Safety
        stay_safe = get_section_text(data, "Stay safe")
        if stay_safe and category_counts["safety"] < target_per_category:
            qs = generate_safety_questions(country, stay_safe)
            for q in qs:
                if category_counts["safety"] < target_per_category:
                    all_questions.append(q)
                    category_counts["safety"] += 1

        # Health
        stay_healthy = get_section_text(data, "Stay healthy")
        if stay_healthy and category_counts["health"] < target_per_category:
            qs = generate_health_questions(country, stay_healthy)
            for q in qs:
                if category_counts["health"] < target_per_category:
                    all_questions.append(q)
                    category_counts["health"] += 1

        # Cultural norms
        respect = get_section_text(data, "Respect")
        if respect and category_counts["cultural_norms"] < target_per_category:
            qs = generate_cultural_questions(country, respect)
            for q in qs:
                if category_counts["cultural_norms"] < target_per_category:
                    all_questions.append(q)
                    category_counts["cultural_norms"] += 1

        # Emergency
        if category_counts["emergency"] < target_per_category:
            qs = generate_emergency_questions(country)
            for q in qs:
                if category_counts["emergency"] < target_per_category:
                    all_questions.append(q)
                    category_counts["emergency"] += 1

        # Currency
        buy = get_section_text(data, "Buy")
        if category_counts["currency"] < target_per_category:
            qs = generate_currency_questions(country, buy)
            for q in qs:
                if category_counts["currency"] < target_per_category:
                    all_questions.append(q)
                    category_counts["currency"] += 1

        # Infrastructure
        connect = get_section_text(data, "Connect")
        if category_counts["infrastructure"] < target_per_category:
            qs = generate_infrastructure_questions(country, connect)
            for q in qs:
                if category_counts["infrastructure"] < target_per_category:
                    all_questions.append(q)
                    category_counts["infrastructure"] += 1

        # Language
        talk = get_section_text(data, "Talk")
        if category_counts["language"] < target_per_category:
            qs = generate_language_questions(country, talk)
            for q in qs:
                if category_counts["language"] < target_per_category:
                    all_questions.append(q)
                    category_counts["language"] += 1

        # Transportation
        get_around = get_section_text(data, "Get around")
        if category_counts["transportation"] < target_per_category:
            qs = generate_transportation_questions(country, get_around)
            for q in qs:
                if category_counts["transportation"] < target_per_category:
                    all_questions.append(q)
                    category_counts["transportation"] += 1

        # Visa
        get_in = get_section_text(data, "Get in")
        if category_counts["visa"] < target_per_category:
            qs = generate_visa_questions(country, get_in)
            for q in qs:
                if category_counts["visa"] < target_per_category:
                    all_questions.append(q)
                    category_counts["visa"] += 1

        # Scams
        if stay_safe and category_counts["scams"] < target_per_category:
            qs = generate_scam_questions(country, stay_safe)
            for q in qs:
                if category_counts["scams"] < target_per_category:
                    all_questions.append(q)
                    category_counts["scams"] += 1

    return all_questions, category_counts


def assign_ids(questions: list[dict]) -> list[dict]:
    """Assign sequential IDs and add source metadata."""
    for i, q in enumerate(questions):
        q["id"] = f"TQA-{i+1:04d}"
        q["source"] = "wikivoyage"
        if "city" not in q:
            q["city"] = None
    return questions


def save_benchmark(questions: list[dict]) -> None:
    """Save benchmark.json."""
    with open(BENCHMARK_FILE, "w") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(questions)} questions to {BENCHMARK_FILE}")


def print_summary(category_counts: dict) -> None:
    """Print category distribution summary."""
    print("\n=== Category Distribution ===")
    total = 0
    for cat, count in sorted(category_counts.items()):
        print(f"  {cat:20s}: {count:3d}/50")
        total += count
    print(f"  {'TOTAL':20s}: {total:3d}/500")


def main() -> None:
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)

    scrape_only = "--scrape-only" in sys.argv
    generate_only = "--generate-only" in sys.argv

    if not generate_only:
        scraped_data = scrape_all_countries()
    else:
        # Load from cache
        print("Loading cached WikiVoyage data...")
        scraped_data = {}
        for cache_file in SOURCES_DIR.glob("*.json"):
            with open(cache_file) as f:
                data = json.load(f)
            scraped_data[data["country"]] = data
        print(f"  Loaded {len(scraped_data)} countries from cache")

    if scrape_only:
        print("\nScrape complete. Run with --generate-only to generate QA pairs.")
        return

    print("\n=== Generating QA Pairs ===\n")
    questions, category_counts = generate_all_questions(scraped_data)
    questions = assign_ids(questions)
    print_summary(category_counts)
    save_benchmark(questions)


if __name__ == "__main__":
    main()
