import streamlit as st
import google.generativeai as genai
import json
import re
import os
import hashlib
from datetime import datetime

try:
    from prompt import LG_SYSTEM_PROMPT
    PROMPT_AVAILABLE = True
except ImportError:
    LG_SYSTEM_PROMPT = "LG Art Director System v5.8 System Prompt Placeholder"
    PROMPT_AVAILABLE = False

APP_TITLE = "LG Art Director System v5.9.0"
APP_CAPTION = "🚀 Editorial Story Arc + Auto-Balance System Integrator"
SYSTEM_GREETING = (
    "설정이 완료되었습니다.\n"
    "**화보의 구체적인 분위기, 의상, 스토리**를 채팅으로 입력해주세요.\n\n"
    "예시: `카멜 코트, 모던한 분위기, 미술관 프리오프닝 데이`"
)

MODEL_OPTIONS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-flash-latest",
    "gemini-pro-latest",
]

MODEL_EXCLUDE_TOKENS = (
    "image",
    "audio",
    "tts",
    "native",
    "preview",
    "exp",
    "embedding",
    "gemma",
    "nano",
    "aqa",
    "imagen",
    "veo",
    "robotics",
)

REGION_OPTIONS = ["EU", "LATAM"]
REGION_LABELS = {
    "EU": "EU(유럽)",
    "LATAM": "LATAM(라틴아메리카)",
}
CITY_OPTIONS = {
    "EU": [
        "Paris (파리)",
        "London (런던)",
        "Rome (로마)",
        "Barcelona (바르셀로나)",
        "Amsterdam (암스테르담)",
        "Berlin (베를린)",
        "Prague (프라하)",
        "Vienna (비엔나)",
        "Madrid (마드리드)",
        "Florence (피렌체)",
        "Venice (베네치아)",
        "Lisbon (리스본)",
        "Athens (아테네)",
        "Munich (뮌헨)",
        "Budapest (부다페스트)",
        "Brussels (브뤼셀)",
        "Zurich (취리히)",
        "Copenhagen (코펜하겐)",
        "Lyon (리옹)",
        "Krakow (크라쿠프)",
    ],
    "LATAM": [
        "Mexico City (멕시코시티)",
        "Sao Paulo (상파울루)",
        "Buenos Aires (부에노스아이레스)",
        "Rio de Janeiro (리우데자네이루)",
        "Bogota (보고타)",
        "Lima (리마)",
        "Santiago (산티아고)",
        "Medellin (메데인)",
        "Cusco (쿠스코)",
        "Havana (아바나)",
        "Cartagena (카르타헤나)",
        "Quito (키토)",
        "Panama City (파나마시티)",
        "Montevideo (몬테비데오)",
        "San Jose (산호세)",
        "La Paz (라파스)",
        "Cancun (칸쿤)",
        "San Juan (산후안)",
        "Brasilia (브라질리아)",
        "Guadalajara (과달라하라)",
    ],
}

GENDER_OPTIONS = ["FEMALE", "MALE", "NON_BINARY"]
GENDER_LABELS = {
    "FEMALE": "여성",
    "MALE": "남성",
    "NON_BINARY": "논바이너리",
}

ETHNICITY_OPTIONS = [
    "Caucasian (코카서스 인종 / 백인)",
    "East Asian (동아시아인)",
    "African (아프리카인 / 흑인)",
    "South Asian (남아시아인)",
    "Southeast Asian (동남아시아인)",
    "Hispanic / Latino (히스패닉 / 라티노)",
    "Middle Eastern (중동인)",
    "Native American (아메리카 원주민)",
    "Pacific Islander (태평양 섬 주민)",
    "Aboriginal Australian (호주 원주민)",
]

OCCUPATION_OPTIONS = [
    "Software Engineer (소프트웨어 엔지니어)",
    "Data Scientist (데이터 사이언티스트)",
    "Doctor (의사)",
    "Nurse (간호사)",
    "Teacher (교사)",
    "Marketing Specialist (마케팅 전문가)",
    "Financial Analyst (금융 분석가)",
    "Attorney / Lawyer (변호사)",
    "Mechanical Engineer (기계 공학자)",
    "Project Manager (프로젝트 매니저)",
    "Content Creator (콘텐츠 크리에이터)",
    "Sales Representative (영업 대표)",
    "Accountant (회계사)",
    "Architect (건축가)",
    "Chef (요리사)",
    "Civil Servant (공무원)",
    "Graphic Designer (그래픽 디자이너)",
    "Logistics Manager (물류 관리자)",
    "Pharmacist (약사)",
    "Pilot (조종사)",
]

CAST_MODE_OPTIONS = ["SINGLE", "MULTI"]
CAST_MODE_LABELS = {
    "SINGLE": "1명",
    "MULTI": "가족구성원",
}

DIVERSITY_OPTIONS = ["SAFE", "FULL", "OFF"]
DIVERSITY_LABELS = {
    "SAFE": "SAFE(기본)",
    "FULL": "FULL(DEI)",
    "OFF": "OFF(최소)",
}
DIVERSITY_HELP = {
    "SAFE": "기본 균형. 과도한 다양성 확장 없이 안전한 범위.",
    "FULL": "다양성을 적극 반영. 인물/스타일 범위를 넓게.",
    "OFF": "다양성 최소화. 입력값 중심으로 고정.",
}

ASPECT_RATIO_OPTIONS = ["9:16", "16:9", "4:5", "1:1"]
ASPECT_RATIO_LABELS = {
    "9:16": "9:16 (세로)",
    "16:9": "16:9 (와이드)",
    "4:5": "4:5 (룩북)",
    "1:1": "1:1 (정사각)",
}

JSON_BLOCK_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def default_settings():
    return {
        "project_id": "LG_AD_2026_CAMPAIGN_01",
        "region": "EU",
        "city": CITY_OPTIONS["EU"][0],
        "target_date": datetime.today().date(),
        "age": 35,
        "gender": "FEMALE",
        "occupation": "직업 없음",
        "ethnicity": "",
        "cast_mode": "SINGLE",
        "family_count": 3,
        "diversity_mode": "SAFE",
        "aspect_ratio": "4:5",
    }


def resolve_api_key(user_input):
    if "GOOGLE_API_KEY" in st.secrets:
        secret_key = str(st.secrets["GOOGLE_API_KEY"]).strip()
        if secret_key:
            return secret_key, "secrets"

    user_key = (user_input or "").strip()
    if user_key:
        return user_key, "input"

    env_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if env_key:
        return env_key, "env"

    return "", ""


def fingerprint_key(api_key):
    if not api_key:
        return ""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]


def load_model_options(api_key):
    if not api_key:
        return MODEL_OPTIONS

    fingerprint = fingerprint_key(api_key)
    cached = st.session_state.get("model_options_cache", {})
    if cached.get("fingerprint") == fingerprint and cached.get("options"):
        return cached["options"]

    try:
        genai.configure(api_key=api_key)
        models = genai.list_models()
        options = []
        for model in models:
            name = getattr(model, "name", "")
            methods = getattr(model, "supported_generation_methods", []) or []
            if "generateContent" not in methods:
                continue
            if name.startswith("models/"):
                name = name.split("/", 1)[1]
            options.append(name)
        options = [
            option
            for option in options
            if option.startswith("gemini-")
            and not any(token in option for token in MODEL_EXCLUDE_TOKENS)
        ]
        options = sorted(set(options))
        if not options:
            options = MODEL_OPTIONS
    except Exception:
        options = MODEL_OPTIONS

    st.session_state["model_options_cache"] = {
        "fingerprint": fingerprint,
        "options": options,
    }
    return options


def build_chat_history(messages):
    history = []
    for msg in messages:
        role = msg.get("role")
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            history.append({"role": "user", "parts": [content]})
        elif role == "assistant":
            history.append({"role": "model", "parts": [content]})
    return history


def get_chat_session(api_key, model_name, history):
    genai.configure(api_key=api_key)

    generation_config = {
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
    }

    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=generation_config,
        system_instruction=LG_SYSTEM_PROMPT,
    )

    return model.start_chat(history=history)


def parse_response(text):
    json_data = None
    clean_text = text

    for match in JSON_BLOCK_RE.finditer(text):
        candidate = match.group(1).strip()
        try:
            json_data = json.loads(candidate)
            clean_text = (text[:match.start()] + text[match.end():]).strip()
            break
        except json.JSONDecodeError:
            continue

    return json_data, clean_text


def format_target_date(value):
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def build_combined_prompt(settings, user_input, model_name, translate_enabled):
    ethnicity_value = settings["ethnicity"].strip() if settings["ethnicity"] else "Auto"
    target_date = format_target_date(settings["target_date"])

    lines = [
        "[SYSTEM_OVERRIDE_DATA]",
        f"Project_ID: {settings['project_id']}",
        f"Region: {settings['region']}",
        f"City: {settings['city']}",
        f"Target_Date: {target_date}",
        f"Fixed_Age: {settings['age']}",
        f"Fixed_Gender: {settings['gender']}",
        f"Fixed_Occupation: {settings['occupation']}",
        f"Fixed_Ethnicity: {ethnicity_value}",
        f"Cast_Mode: {settings['cast_mode']}",
        f"Diversity_Mode: {settings['diversity_mode']}",
        f"Aspect_Ratio: {settings['aspect_ratio']}",
        f"Model_Version: {model_name}",
    ]

    if settings.get("cast_mode") == "MULTI":
        lines.append(f"Family_Count: {settings.get('family_count', 3)}")

    if translate_enabled:
        lines.extend(
            [
                "",
                "[OUTPUT_TRANSLATION]",
                "응답에 영어가 포함되면 마지막에 한국어 번역 섹션을 추가하세요.",
                "한국어 원문은 그대로 유지하고, JSON 블록은 번역하지 마세요.",
            ]
        )

    lines.extend(["", "[USER_CREATIVE_DIRECTION]", user_input])
    return "\n".join(lines).strip()

def mark_family_touched():
    st.session_state["family_count_touched"] = True


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .stChatMessage { font-family: 'Helvetica', sans-serif; }
    div[data-testid="stExpander"] {
        border: 1px solid #2b3447;
        border-radius: 8px;
        background-color: #1c2333;
    }
    div[data-testid="stExpander"] [data-testid="stMarkdownContainer"] {
        color: #f8fafc;
    }
    div[data-testid="stExpander"] svg,
    div[data-testid="stExpander"] path {
        color: #f8fafc;
        fill: currentColor;
    }
    button[data-testid="stCopyButton"] {
        background-color: rgba(242, 94, 0, 0.5) !important;
        border: 1px solid rgba(242, 94, 0, 0.65) !important;
        border-radius: 6px !important;
    }
    button[data-testid="stCopyButton"] svg,
    button[data-testid="stCopyButton"] path {
        color: #ffffff !important;
        fill: #ffffff !important;
    }
    .json-header {
        color: #F25E00;
        font-weight: bold;
    }
    section[data-testid="stSidebar"] {
        background-color: #222a3a;
        border-right: 1px solid #1f2937;
        width: 42rem !important;
        min-width: 42rem !important;
        max-width: 42rem !important;
    }
    section[data-testid="stSidebar"] > div {
        width: 42rem !important;
        min-width: 42rem !important;
        max-width: 42rem !important;
    }
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea,
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div,
    section[data-testid="stSidebar"] div[data-baseweb="input"] > div,
    section[data-testid="stSidebar"] div[data-baseweb="datepicker"] > div {
        background-color: #0f1117 !important;
    }
    .sidebar-label {
        font-size: 0.8rem;
        font-weight: 600;
        color: #ffffff;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }
    .context-box {
        background-color: #f0f2f6;
        padding: 10px 15px;
        border-radius: 8px;
        font-size: 0.9rem;
        color: #333;
        margin-bottom: 20px;
    }
    .context-box .context-meta {
        font-size: 0.8rem;
        color: #666;
    }
    .context-flash {
        animation: contextFlash 0.45s ease-in-out;
    }
    @keyframes contextFlash {
        0% { background-color: #ffffff; }
        100% { background-color: #f0f2f6; }
    }
</style>
""",
    unsafe_allow_html=True,
)

translate_enabled = st.checkbox("한글 번역 함께 출력", value=False, key="translate_enabled")
if translate_enabled:
    st.caption("AI 응답에 영어가 있으면 하단에 한글 번역 섹션이 추가됩니다.")

if "applied_settings" not in st.session_state:
    st.session_state["applied_settings"] = default_settings()

api_key = ""
api_source = ""
model_option = MODEL_OPTIONS[0]
flash_context = False

with st.sidebar:
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
            <div style="display: flex; align-items: center;">
                <svg viewBox="0 0 593 114" xmlns="http://www.w3.org/2000/svg" style="height:30px; width:auto; display:block;">
                    <path d="M487.606 59.5181H473.577V111.884H452.05V59.5181H438.021V41.0145H452.05V19.9712H473.577V41.0145H487.606V59.5181Z" fill="#F25E00"/>
                    <path d="M417.277 6.78893C421.067 6.78893 424.211 8.03863 426.711 10.538C429.21 13.0374 430.46 16.1818 430.46 19.9712C430.46 23.7606 429.21 26.905 426.711 29.4044C424.211 31.9038 421.067 33.1535 417.277 33.1535C413.488 33.1535 410.344 31.9038 407.844 29.4044C405.345 26.905 404.095 23.7606 404.095 19.9712C404.095 16.1818 405.345 13.0374 407.844 10.538C410.344 8.03863 413.488 6.78893 417.277 6.78893ZM428.041 112.126H406.514V41.0145H428.041V112.126Z" fill="#F25E00"/>
                    <path d="M323.085 113.578C315.99 113.578 309.621 111.965 303.977 108.74C298.414 105.596 294.06 101.202 290.916 95.5578C287.771 89.914 286.199 83.5446 286.199 76.4495C286.199 69.3544 287.771 62.985 290.916 57.3412C294.06 51.6974 298.414 47.3033 303.977 44.1589C309.621 40.9339 315.99 39.3214 323.085 39.3214C330.18 39.3214 336.509 40.9339 342.073 44.1589C347.716 47.3033 352.11 51.6974 355.255 57.3412C358.399 62.985 359.971 69.3544 359.971 76.4495C359.971 78.7876 359.81 81.0855 359.488 83.343H307.605C308.411 87.4549 310.185 90.6396 312.926 92.8971C315.668 95.1546 319.054 96.2834 323.085 96.2834C326.149 96.2834 328.85 95.7996 331.188 94.8321C333.607 93.784 335.26 92.4134 336.147 90.7202H357.795C356.585 95.2353 354.328 99.1859 351.022 102.572C347.716 106.039 343.645 108.74 338.807 110.675C333.97 112.61 328.729 113.578 323.085 113.578ZM338.928 69.4351C338.041 65.1619 336.227 61.9369 333.486 59.76C330.745 57.5025 327.278 56.3737 323.085 56.3737C318.893 56.3737 315.466 57.5025 312.805 59.76C310.145 61.9369 308.371 65.1619 307.484 69.4351H338.928Z" fill="#F25E00"/>
                    <path d="M244.354 85.8827L235.768 95.5578V111.884H214.241V10.2961H235.768V69.9188L260.802 41.0145H284.748L257.537 71.2491L286.199 111.884H261.648L244.354 85.8827Z" fill="#F25E00"/>
                    <path d="M156.148 113.578C149.456 113.578 143.489 111.965 138.249 108.74C133.008 105.596 128.936 101.202 126.034 95.5578C123.131 89.914 121.68 83.5446 121.68 76.4495C121.68 69.3544 123.131 62.985 126.034 57.3412C128.936 51.6974 133.008 47.3033 138.249 44.1589C143.489 40.9339 149.456 39.3214 156.148 39.3214C165.258 39.3214 172.031 42.3045 176.465 48.2708V41.0145H197.992V111.884H176.465V104.628C172.031 110.594 165.258 113.578 156.148 113.578ZM159.534 95.195C164.775 95.195 168.967 93.4615 172.112 89.9946C175.256 86.4471 176.828 81.932 176.828 76.4495C176.828 70.9669 175.256 66.4922 172.112 63.0253C168.967 59.4778 164.775 57.704 159.534 57.704C154.454 57.704 150.383 59.4778 147.319 63.0253C144.255 66.4922 142.723 70.9669 142.723 76.4495C142.723 81.932 144.255 86.4471 147.319 89.9946C150.383 93.4615 154.454 95.195 159.534 95.195Z" fill="#F25E00"/>
                    <path d="M0 41.0145H21.527V47.7871C23.7039 44.8845 26.163 42.748 28.9043 41.3773C31.7262 40.0067 35.0722 39.3214 38.9422 39.3214C43.3766 39.3214 47.4079 40.2083 51.036 41.982C54.6642 43.6752 57.6473 46.1746 59.9855 49.4802C62.6461 46.0939 65.9115 43.5542 69.7815 41.8611C73.6515 40.1679 78.2472 39.3214 83.5685 39.3214C88.9704 39.3214 93.7273 40.6114 97.8392 43.1914C101.951 45.6908 105.136 49.319 107.393 54.0759C109.651 58.8328 110.78 64.4363 110.78 70.8863V111.884H89.2526V74.5145C89.2526 69.1126 88.2448 65.0006 86.2291 62.1787C84.2135 59.2762 81.2303 57.825 77.2797 57.825C73.8128 57.825 71.1118 59.1553 69.1768 61.8159C67.3224 64.4766 66.3146 68.3466 66.1534 73.426V111.884H44.6263V74.5145C44.6263 69.1126 43.6185 65.0006 41.6028 62.1787C39.5872 59.2762 36.604 57.825 32.6534 57.825C29.1865 57.825 26.4855 59.1553 24.5505 61.8159C22.6961 64.4766 21.6883 68.3466 21.527 73.426V111.884H0V41.0145Z" fill="#F25E00"/>
                    <path d="M512.897 32C512.897 14.3269 527.224 0 544.897 0H560.897C578.57 0 592.897 14.3269 592.897 32C592.897 49.6731 578.57 64 560.897 64H544.897C527.224 64 512.897 49.6731 512.897 32Z" fill="#F25E00"/>
                    <path d="M575.051 13.6008V49.134H567.116V13.6008H575.051Z" fill="white"/>
                    <path d="M552.213 42.2454H538.435L535.95 49.134H527.753L541.531 13.6008H549.771L563.548 49.134H554.698L552.213 42.2454ZM549.771 35.3567L545.324 22.9746L540.877 35.3567H549.771Z" fill="white"/>
                </svg>
            </div>
            <div>
                <div style="font-weight: bold; font-size: 1.1rem;">Art Director</div>
                <div style="font-size: 0.7rem; color: #888;">v5.8 PROFESSIONAL</div>
            </div>
        </div>
    """,
        unsafe_allow_html=True,
    )

    if not PROMPT_AVAILABLE:
        st.warning("prompt.py를 찾지 못했습니다. 기본 프롬프트로 동작합니다.")

    with st.expander("🔐 시스템 설정", expanded=False):
        # 1. 시크릿(Streamlit Cloud/Local secrets.toml) 먼저 확인
        if "GOOGLE_API_KEY" in st.secrets:
            st.success("✅ API 키가 시스템 시크릿에서 로드되었습니다.")
            api_key = str(st.secrets["GOOGLE_API_KEY"]).strip()
            api_source = "secrets"

        # 2. 시크릿이 없으면 입력창 표시
        else:
            api_key_input = st.text_input(
                "Google API Key",
                type="password",
                key="api_key_input",
                help="Streamlit Secrets에 키가 설정되지 않았을 때 사용됩니다.",
            )
            # 입력값 또는 환경변수 확인
            api_key, api_source = resolve_api_key(api_key_input)

        # 상태 메시지
        if api_source == "input":
            st.info("입력된 API 키를 사용합니다.")
        elif api_source == "env":
            st.info("환경변수에서 API 키를 찾았습니다.")
        elif not api_key:
            st.warning("⚠️ API 키가 필요합니다. 설정 메뉴에서 입력하거나 Secrets를 설정하세요.")

        model_options = load_model_options(api_key)
        if "model_option" not in st.session_state or st.session_state["model_option"] not in model_options:
            st.session_state["model_option"] = model_options[0]
        model_option = st.selectbox(
            "모델 선택",
            model_options,
            key="model_option",
        )

    st.markdown("---")
    st.markdown('<p class="sidebar-label">🎛️ Control Tower</p>', unsafe_allow_html=True)

    settings = st.session_state["applied_settings"]
    if "family_count" not in settings:
        settings["family_count"] = 3
        st.session_state["applied_settings"] = settings
    previous_settings = settings.copy()

    st.markdown('<p class="sidebar-label">📍 프로젝트 정보</p>', unsafe_allow_html=True)
    project_id = st.text_input(
        "프로젝트 ID",
        value=settings["project_id"],
        key="project_id",
    )

    col_region, col_city = st.columns(2)
    with col_region:
        region = st.selectbox(
            "지역",
            REGION_OPTIONS,
            index=REGION_OPTIONS.index(settings["region"]),
            format_func=lambda x: REGION_LABELS[x],
            key="region",
        )
    city_list = CITY_OPTIONS[region]
    current_city = st.session_state.get("city", settings["city"])
    if current_city not in city_list:
        current_city = city_list[0]
        st.session_state["city"] = current_city
    with col_city:
        city = st.selectbox(
            "도시",
            city_list,
            index=city_list.index(current_city),
            key="city",
        )

    target_date = st.date_input(
        "타깃 일정",
        value=settings["target_date"],
        key="target_date",
    )

    st.markdown("---")
    st.markdown('<p class="sidebar-label">👤 Fixed Persona</p>', unsafe_allow_html=True)

    col_age, col_gender = st.columns([1, 1.5])
    with col_age:
        age = st.number_input(
            "나이",
            min_value=0,
            max_value=100,
            value=int(settings["age"]),
            key="age",
        )
    with col_gender:
        gender = st.selectbox(
            "성별",
            GENDER_OPTIONS,
            index=GENDER_OPTIONS.index(settings["gender"]),
            format_func=lambda x: GENDER_LABELS[x],
            key="gender",
        )

    occupation_options = ["직접 입력", "직업 없음"] + OCCUPATION_OPTIONS
    current_occupation = settings["occupation"] or "직업 없음"
    if current_occupation in OCCUPATION_OPTIONS:
        occupation_index = occupation_options.index(current_occupation)
        occupation_custom = ""
    elif current_occupation in ("직업 없음", ""):
        occupation_index = occupation_options.index("직업 없음")
        occupation_custom = ""
    else:
        occupation_index = occupation_options.index("직접 입력")
        occupation_custom = current_occupation

    occupation_choice = st.selectbox(
        "직업",
        occupation_options,
        index=occupation_index,
        key="occupation_choice",
    )
    occupation_input = ""
    if occupation_choice == "직접 입력":
        occupation_input = st.text_input(
            "직업 직접 입력",
            value=occupation_custom,
            placeholder="직접 입력",
            key="occupation_custom",
        )
        occupation = occupation_input.strip() or "직업 없음"
    elif occupation_choice == "직업 없음":
        occupation = "직업 없음"
    else:
        occupation = occupation_choice
    ethnicity_options = ["직접 입력", "선택 안 함"] + ETHNICITY_OPTIONS
    current_ethnicity = settings["ethnicity"] or "선택 안 함"
    if current_ethnicity in ETHNICITY_OPTIONS:
        ethnicity_index = ethnicity_options.index(current_ethnicity)
        ethnicity_custom = ""
    elif current_ethnicity in ("선택 안 함", ""):
        ethnicity_index = ethnicity_options.index("선택 안 함")
        ethnicity_custom = ""
    else:
        ethnicity_index = ethnicity_options.index("직접 입력")
        ethnicity_custom = current_ethnicity

    ethnicity_choice = st.selectbox(
        "인종/특징",
        ethnicity_options,
        index=ethnicity_index,
        key="ethnicity_choice",
    )
    if ethnicity_choice == "직접 입력":
        ethnicity_input = st.text_input(
            "인종/특징 직접 입력",
            value=ethnicity_custom,
            placeholder="직접 입력",
            key="ethnicity_custom",
        )
        ethnicity = ethnicity_input.strip()
    elif ethnicity_choice == "선택 안 함":
        ethnicity = ""
    else:
        ethnicity = ethnicity_choice

    st.markdown("---")
    st.markdown('<p class="sidebar-label">⚙️ 출력 제어</p>', unsafe_allow_html=True)

    if "family_count_touched" not in st.session_state:
        st.session_state["family_count_touched"] = False
    prev_cast_mode = st.session_state.get("cast_mode_prev", settings["cast_mode"])

    cast_mode = st.radio(
        "캐스팅 모드",
        CAST_MODE_OPTIONS,
        index=CAST_MODE_OPTIONS.index(settings["cast_mode"]),
        format_func=lambda x: CAST_MODE_LABELS[x],
        horizontal=True,
        key="cast_mode",
    )
    if cast_mode != prev_cast_mode:
        st.session_state["family_count_touched"] = False
    st.session_state["cast_mode_prev"] = cast_mode
    if cast_mode == "MULTI":
        family_count = st.number_input(
            "가족 구성원 수",
            min_value=2,
            max_value=10,
            value=int(settings.get("family_count", 3)),
            key="family_count",
            on_change=mark_family_touched,
        )
    else:
        family_count = settings.get("family_count", 3)
    diversity_mode = st.selectbox(
        "다양성 모드",
        DIVERSITY_OPTIONS,
        index=DIVERSITY_OPTIONS.index(settings["diversity_mode"]),
        format_func=lambda x: DIVERSITY_LABELS[x],
        key="diversity_mode",
    )
    st.caption(DIVERSITY_HELP.get(diversity_mode, ""))
    aspect_ratio = st.selectbox(
        "비율",
        ASPECT_RATIO_OPTIONS,
        index=ASPECT_RATIO_OPTIONS.index(settings["aspect_ratio"]),
        format_func=lambda x: ASPECT_RATIO_LABELS[x],
        key="aspect_ratio",
    )

    new_settings = {
        "project_id": project_id,
        "region": region,
        "city": city,
        "target_date": target_date,
        "age": age,
        "gender": gender,
        "occupation": occupation,
        "ethnicity": ethnicity,
        "cast_mode": cast_mode,
        "family_count": family_count,
        "diversity_mode": diversity_mode,
        "aspect_ratio": aspect_ratio,
    }
    flash_context = new_settings != previous_settings
    st.session_state["applied_settings"] = new_settings

    st.markdown("---")
    st.caption(f"시스템: LG Step1 Schema v5.8\n모델: {model_option}")

    if st.button("🗑️ 대화 초기화", type="secondary"):
        for key in ("messages", "model_messages", "chat_session"):
            st.session_state.pop(key, None)
        st.rerun()

st.title(APP_TITLE)
st.caption(APP_CAPTION)

applied_settings = st.session_state["applied_settings"]
city_list = CITY_OPTIONS[applied_settings["region"]]
if applied_settings["city"] not in city_list:
    applied_settings["city"] = city_list[0]
    st.session_state["applied_settings"] = applied_settings
if "family_count" not in applied_settings:
    applied_settings["family_count"] = 3
    st.session_state["applied_settings"] = applied_settings

context_gender = GENDER_LABELS[applied_settings["gender"]]
context_cast = CAST_MODE_LABELS[applied_settings["cast_mode"]]
context_diversity = DIVERSITY_LABELS[applied_settings["diversity_mode"]]
context_ratio = ASPECT_RATIO_LABELS[applied_settings["aspect_ratio"]]
context_date = format_target_date(applied_settings["target_date"])
context_ethnicity = applied_settings["ethnicity"].strip() or "Auto"
context_family = applied_settings.get("family_count", 3)
context_family_text = ""
if applied_settings["cast_mode"] == "MULTI" and st.session_state.get("family_count_touched"):
    context_family_text = f" | 가족 구성원: {context_family}명"

st.markdown(
    f"""
    <div class="context-box{' context-flash' if flash_context else ''}">
        <strong>현재 컨텍스트</strong><br>
        지역: {REGION_LABELS[applied_settings["region"]]} / 도시: {applied_settings["city"]} /
        {applied_settings["age"]}세 {context_gender} / {applied_settings["occupation"]} / {context_ethnicity}
        <br>
        <span class="context-meta">타깃: {context_date} | 모드: {context_cast}{context_family_text} | 다양성: {context_diversity} | 비율: {context_ratio}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": SYSTEM_GREETING}]

if "model_messages" not in st.session_state:
    st.session_state["model_messages"] = []

api_key_fingerprint = fingerprint_key(api_key)
if (
    st.session_state.get("active_model") != model_option
    or st.session_state.get("api_key_fingerprint") != api_key_fingerprint
):
    st.session_state["chat_session"] = None
    st.session_state["active_model"] = model_option
    st.session_state["api_key_fingerprint"] = api_key_fingerprint

if st.session_state.get("chat_session") is None and api_key:
    try:
        history = build_chat_history(st.session_state["model_messages"])
        st.session_state["chat_session"] = get_chat_session(api_key, model_option, history)
    except Exception as e:
        st.error(f"모델 연결 실패: {e}")

for msg in st.session_state["messages"]:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    else:
        with st.chat_message("assistant"):
            json_data, text_content = parse_response(msg["content"])

            if json_data:
                with st.expander("📦 STEP 2 데이터 핸드오프(JSON)", expanded=False):
                    st.json(json_data)
                    st.caption("이 JSON 데이터를 복사하여 이미지 생성 파이프라인에 전달하세요.")

            if text_content:
                st.markdown(text_content)

if user_input := st.chat_input("추가적인 컨셉이나 지시사항을 입력하세요..."):
    if not api_key:
        st.error("API 키를 사이드바에서 설정해주세요.")
        st.stop()

    if st.session_state.get("chat_session") is None:
        st.error("채팅 세션이 초기화되지 않았습니다. 새로고침 해주세요.")
        st.stop()

    combined_prompt = build_combined_prompt(
        st.session_state["applied_settings"],
        user_input,
        model_option,
        translate_enabled,
    )

    st.chat_message("user").write(user_input)
    st.session_state["messages"].append({"role": "user", "content": user_input})
    st.session_state["model_messages"].append({"role": "user", "content": combined_prompt})

    with st.spinner("Art Director가 설정값과 지시사항을 분석 중입니다..."):
        try:
            chat = st.session_state["chat_session"]
            response = chat.send_message(combined_prompt)
            full_response = response.text or ""

            with st.chat_message("assistant"):
                json_data, text_content = parse_response(full_response)

                if json_data:
                    with st.expander("📦 STEP 2 데이터 핸드오프(JSON)", expanded=True):
                        st.json(json_data)
                        st.info("✅ 데이터가 성공적으로 생성되었습니다.")

                if text_content:
                    st.markdown(text_content)

            st.session_state["messages"].append(
                {"role": "assistant", "content": full_response}
            )
            st.session_state["model_messages"].append(
                {"role": "assistant", "content": full_response}
            )
        except Exception as e:
            st.error(f"생성 중 오류 발생: {e}")
