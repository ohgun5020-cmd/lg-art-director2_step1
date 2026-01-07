# LG Art Director System v5.9.0

매거진 화보 수준의 AI 이미지 프롬프트 생성 시스템

## 구조

```
lg_art_director_v5.9.0/
├── app.py                 # Streamlit 메인 앱
├── prompt.py              # 시스템 프롬프트 로더
├── prompts/               # 시스템 프롬프트 모듈
│   ├── INDEX.md           # 로드 순서 정의
│   ├── 00_core_contract.md      # 보안 + 스키마 + 규칙 (LGAD-CORE)
│   ├── 10_cast_variation_engine.md  # 기후/캐스팅/다양성 (LGAD-CAST)
│   └── 20_world_style_output.md     # 조명/지역/출력 (LGAD-WORLD)
├── schemas/
│   └── LG_Step1_Schema_v1_1.json    # JSON 스키마
├── .streamlit/
│   └── secrets.toml       # API 키 설정
├── requirements.txt       # 의존성
├── check.py              # API 테스트 스크립트
├── AGENTS.md             # Codex 작업 규칙
└── .gitignore
```

## 설치 및 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 실행
streamlit run app.py
```

## 버전업 방법

`prompts/` 폴더의 md 파일만 교체하면 자동 반영됨:
1. 해당 md 파일 덮어쓰기
2. 앱 재시작

## 프롬프트 로드 순서

1. `00_core_contract.md` (LGAD-CORE) - 최우선
2. `10_cast_variation_engine.md` (LGAD-CAST)
3. `20_world_style_output.md` (LGAD-WORLD)

충돌 시: CORE > CAST > WORLD 순으로 우선

## 변경사항 (v5.8 → v5.9.0)

- 시스템 프롬프트 모듈화 (단일 파일 → 3개 md 파일)
- prompt.py를 로더 역할로 변경
- md 파일만 교체하면 버전업 가능
