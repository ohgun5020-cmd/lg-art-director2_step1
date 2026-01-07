import streamlit as st
import google.generativeai as genai
import json
import os
from datetime import datetime
from hashlib import sha1

APP_TITLE = "LG Art Director System - STEP 1 (Character JSON) v1.0.0"
APP_CAPTION = "Step1: 캐릭터/페르소나 + Step2 오버라이드(JSON) 생성"

MODEL_OPTIONS = [
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-2.0-flash-exp",
]

REGION_OPTIONS = ["EU", "LATAM"]
REGION_LABELS = {"EU": "EU(유럽)", "LATAM": "LATAM(라틴아메리카)"}
CITY_OPTIONS = {
    "EU": [
        "Paris (파리)",
        "London (런던)",
        "Rome (로마)",
        "Barcelona (바르셀로나)",
        "Berlin (베를린)",
        "Amsterdam (암스테르담)",
        "Prague (프라하)",
        "Vienna (비엔나)",
    ],
    "LATAM": [
        "Mexico City (멕시코시티)",
        "São Paulo (상파울루)",
        "Buenos Aires (부에노스아이레스)",
        "Bogotá (보고타)",
        "Lima (리마)",
        "Santiago (산티아고)",
        "Rio de Janeiro (리우)",
    ],
}

SEASON_OPTIONS = ["SPRING", "SUMMER", "FALL", "WINTER"]
ASPECT_RATIO_OPTIONS = ["1:1", "4:5", "3:4", "16:9", "9:16"]

HOUSING_TYPE_OPTIONS = ["APARTMENT", "HOUSE", "PENTHOUSE", "STUDIO", "LOFT"]
INTERIOR_STYLE_OPTIONS = [
    "PARIS_STYLE",
    "LONDON_STYLE",
    "ROME_STYLE",
    "BARCELONA_STYLE",
    "MODERN_MINIMAL",
    "CLASSIC_LUXURY",
    "INDUSTRIAL_LOFT",
    "SCANDI_WARM",
]
OUTPUT_PRESET_OPTIONS = ["BASIC", "DETAIL_PLUS", "NEGATIVE_PLUS", "COMPOSITE_READY"]

DEFAULT_SYSTEM_PROMPT = """You generate STRICT JSON for STEP 1 of an art-direction pipeline.
Rules:
- Output MUST be valid JSON only. No markdown. No comments. No trailing commas.
- Return either a JSON object named "character" OR a full object containing a "character" field.
- Keep values concise and production-ready.
Character fields:
gender_presentation, ethnicity_or_origin, hair, makeup, outfit, accessories, body_language,
facial_expression, vibe_keywords, camera_notes, lighting_notes.
"""

def get_api_key() -> str | None:
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            return st.secrets["GOOGLE_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GOOGLE_API_KEY")

def stable_project_id(region: str, city: str, seed_text: str) -> str:
    raw = f"{region}|{city}|{seed_text}|{datetime.utcnow().strftime('%Y%m%d')}"
    return "LG_AD_2026_STEP1_" + sha1(raw.encode("utf-8")).hexdigest()[:10].upper()

def default_step2_overrides(city: str) -> dict:
    city_key = (city or "").split(" (")[0].strip().lower()
    style_map = {
        "paris": "PARIS_STYLE",
        "london": "LONDON_STYLE",
        "rome": "ROME_STYLE",
        "barcelona": "BARCELONA_STYLE",
    }
    interior_style = style_map.get(city_key, "MODERN_MINIMAL")
    return {
        "housing_type": "APARTMENT",
        "interior_style": interior_style,
        "room_types": ["Kitchen", "Living", "Bedroom", "Laundry"],
        "entropy_level": 5,
        "output_preset": "COMPOSITE_READY",
    }

def build_step1_json(
    region: str,
    city: str,
    season: str,
    aspect_ratio: str,
    fashion_color: str,
    fashion_color_name: str,
    age: int,
    occupation: str,
    biometric_ids: list[str],
    concept: str,
    concept_summary: str,
    step2_overrides: dict,
    character: dict,
    project_id: str,
) -> dict:
    return {
        "meta": {
            "schema_version": "step1.v1",
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        },
        "project_id": project_id,
        "region": region,
        "city": city,
        "season": season,
        "aspect_ratio": aspect_ratio,
        "fashion_color": fashion_color,
        "fashion_color_name": fashion_color_name,
        "biometric_ids": biometric_ids,
        "fixed": {"age": age, "occupation": occupation},
        "concept": concept,
        "concept_summary": concept_summary,
        "character": character,
        "step2_overrides": step2_overrides,
    }

def generate_character_json(model_name: str, system_prompt: str, user_payload: dict) -> tuple[dict | None, str | None]:
    api_key = get_api_key()
    if not api_key:
        return None, "GOOGLE_API_KEY가 없습니다. .streamlit/secrets.toml 또는 환경변수에 설정하세요."

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name=model_name, system_instruction=system_prompt)

    try:
        resp = model.generate_content(
            json.dumps(user_payload, ensure_ascii=False),
            generation_config={"temperature": 0.5, "max_output_tokens": 1200},
        )
        txt = (resp.text or "").strip()
        data = json.loads(txt)
        if not isinstance(data, dict):
            return None, "모델 응답이 JSON object가 아님"
        return data, None
    except json.JSONDecodeError as e:
        return None, f"모델 응답 JSON 파싱 실패: {e}"
    except Exception as e:
        return None, f"생성 실패: {e}"

st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)
st.caption(APP_CAPTION)

with st.sidebar:
    st.subheader("모델 설정")
    model_name = st.selectbox("Gemini 모델", MODEL_OPTIONS, index=1)

    st.divider()
    st.subheader("지역")
    region = st.selectbox("Region", REGION_OPTIONS, format_func=lambda x: REGION_LABELS.get(x, x), index=0)
    city = st.selectbox("City", CITY_OPTIONS[region], index=0)
    season = st.selectbox("Season", SEASON_OPTIONS, index=3)
    aspect_ratio = st.selectbox("Aspect Ratio", ASPECT_RATIO_OPTIONS, index=1)

    st.divider()
    st.subheader("고정값(Fixed)")
    age = st.number_input("Age", min_value=18, max_value=70, value=35, step=1)
    occupation = st.text_input("Occupation", value="Gallery Curator")

    st.divider()
    st.subheader("패션 톤")
    fashion_color = st.text_input("Fashion Color (Hex)", value="#C19A6B")
    fashion_color_name = st.text_input("Fashion Color Name", value="Camel")

    st.divider()
    st.subheader("Biometric IDs (선택)")
    biometric_ids_raw = st.text_area("예: id1,id2,id3", value="")

    st.divider()
    st.subheader("Step2 Overrides")
    auto_overrides = st.toggle("도시 기반 자동 오버라이드 사용", value=True)

colA, colB = st.columns([1, 1], gap="large")

with colA:
    st.subheader("컨셉 입력")
    concept = st.text_area("Concept", value="", height=120, placeholder="예: 카멜 코트, 모던한 분위기, 미술관 프리오프닝 데이")
    concept_summary = st.text_area("Concept Summary", value="", height=160, placeholder="예: 주인공 페르소나/스토리/촬영 톤 요약")

with colB:
    st.subheader("Step2 Overrides 상세")
    base = default_step2_overrides(city)
    if auto_overrides:
        step2_overrides = base
        st.info("자동 오버라이드 ON. Step2에서 바로 먹히는 값으로 출력됨.")
    else:
        housing_type = st.selectbox("Housing Type", HOUSING_TYPE_OPTIONS, index=0)
        interior_style = st.selectbox("Interior Style", INTERIOR_STYLE_OPTIONS, index=0)
        room_types = st.multiselect(
            "Room Types (4개 추천)",
            ["Kitchen", "Living", "Dining", "Bedroom", "Bathroom", "Laundry", "Office", "Hallway", "Balcony"],
            default=["Kitchen", "Living", "Bedroom", "Laundry"],
        )
        entropy_level = st.slider("Entropy Level (1~10)", min_value=1, max_value=10, value=5)
        output_preset = st.selectbox("Output Preset", OUTPUT_PRESET_OPTIONS, index=3)
        step2_overrides = {
            "housing_type": housing_type,
            "interior_style": interior_style,
            "room_types": room_types[:4],
            "entropy_level": int(entropy_level),
            "output_preset": output_preset,
        }

st.divider()

with st.expander("고급: 시스템 프롬프트(기본값 추천)", expanded=False):
    system_prompt = st.text_area("SYSTEM PROMPT", value=DEFAULT_SYSTEM_PROMPT, height=180)

generate = st.button("STEP1 JSON 생성", type="primary", use_container_width=True)

if generate:
    seed = (concept + "|" + concept_summary).strip()
    if not seed:
        st.error("Concept 또는 Concept Summary 중 최소 1개는 넣어.")
    else:
        biometric_ids = [x.strip() for x in biometric_ids_raw.split(",") if x.strip()]
        project_id = stable_project_id(region, city, seed)

        user_payload = {
            "region": region,
            "city": city,
            "season": season,
            "aspect_ratio": aspect_ratio,
            "fixed": {"age": int(age), "occupation": occupation},
            "fashion_color": fashion_color,
            "fashion_color_name": fashion_color_name,
            "concept": concept,
            "concept_summary": concept_summary,
        }

        character_json, err = generate_character_json(model_name, system_prompt, user_payload)
        if err:
            st.error(err)
        else:
            character = character_json.get("character", character_json)
            if not isinstance(character, dict):
                st.error("character JSON이 object가 아님")
            else:
                out = build_step1_json(
                    region=region,
                    city=city,
                    season=season,
                    aspect_ratio=aspect_ratio,
                    fashion_color=fashion_color,
                    fashion_color_name=fashion_color_name,
                    age=int(age),
                    occupation=occupation,
                    biometric_ids=biometric_ids,
                    concept=concept,
                    concept_summary=concept_summary,
                    step2_overrides=step2_overrides,
                    character=character,
                    project_id=project_id,
                )

                pretty = json.dumps(out, ensure_ascii=False, indent=2)
                st.success("완료. 아래 JSON을 Step2에 그대로 복붙해.")
                st.code(pretty, language="json")

                st.download_button(
                    "STEP1 JSON 다운로드 (.json)",
                    data=pretty.encode("utf-8"),
                    file_name=f"{project_id}_step1.json",
                    mime="application/json",
                    use_container_width=True,
                )