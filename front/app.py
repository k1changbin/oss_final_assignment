import streamlit as st
import requests
import os

# 페이지 기본 설정
st.set_page_config(page_title="축구화 추천 프로그램", layout="wide")

# 백엔드 API URL 설정 (EC2/로컬 대응)
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

# 외부 파일로부터 퀴즈 데이터 가져오기
from quiz_data import QUIZ_DATA

# 세션 상태 초기화
if "page" not in st.session_state:
    st.session_state.page = "main"
if "current_q" not in st.session_state:
    st.session_state.current_q = 0
if "answers" not in st.session_state:
    st.session_state.answers = {}

# 상단 레이아웃
st.title("축구화 추천 프로그램")
st.text("학번: 2023204035 | 이름: 권창빈")
st.divider()

# 메인 화면
if st.session_state.page == "main":
    st.subheader("나의 축구 성향과 신체 조건에 딱 들어맞는 축구화 추천 프로그램입니다.")
    
    st.write("""
    본 프로그램은 사용자의 플레이 스타일, 발볼 너비, 선호 무게감, 구장 환경 및 예산 범위 등 5가지 핵심 요소를 종합 분석합니다.
    분석된 정보는 FastAPI 백엔드 연산 서버의 다차원 가중치 채점 알고리즘을 거쳐 각 주요 브랜드(Nike, Adidas, Puma)의 
    가장 높은 적합도를 기록한 모델과 가격 정보를 도출합니다.
    """)
    st.write("")
    
    if st.button("추천 프로그램 시작하기", width="stretch", type="primary", key="btn_start_analysis"):
        st.session_state.page = "quiz"
        st.session_state.current_q = 0
        st.session_state.answers = {}
        st.rerun()

# 퀴즈 화면
elif st.session_state.page == "quiz":
    st.subheader("추천을 위한 정보 입력")
    
    total_q = len(QUIZ_DATA)
    current_q = st.session_state.current_q
    
    # 사이드바 실시간 분석 트래킹
    with st.sidebar:
        st.header("실시간 입력 상태")
        st.write("---")
        
        for idx in range(total_q):
            cat_ko = {
                "priority": "선호 성능",
                "foot_width": "발볼 너비",
                "weight": "선호 무게",
                "ground": "구장 환경",
                "budget": "예산 범위"
            }[QUIZ_DATA[idx]["category"]]
            ans_text = st.session_state.answers.get(idx)
            if ans_text:
                st.write(f"- **{cat_ko}**: {ans_text.split('(')[0].strip()} (완료)")
            else:
                st.write(f"- **{cat_ko}**: 대기 중")

    # 메인 퀴즈
    st.write(f"**문항 {current_q + 1} / {total_q}**")
    st.progress((current_q + 1) / total_q)
    st.divider()
    
    q_item = QUIZ_DATA[current_q]
    choices_text = [c["text"] for c in q_item["choices"]]
    
    # 이전 답변 자동 바인딩
    default_index = None
    if current_q in st.session_state.answers:
        if st.session_state.answers[current_q] in choices_text:
            default_index = choices_text.index(st.session_state.answers[current_q])
            
    st.caption(f"측정 속성: {q_item['category'].upper()}")
    
    selected = st.radio(q_item["question"], choices_text, index=default_index, key=f"radio_{current_q}")
    st.write("")
    
    col1, col2 = st.columns(2)
    with col1:
        if current_q > 0:
            if st.button("이전 문항", width="stretch"):
                st.session_state.answers[current_q] = selected
                st.session_state.current_q -= 1
                st.rerun()
                
    with col2:
        if current_q < total_q - 1:
            if st.button("다음 문항", width="stretch", type="primary", disabled=(selected is None)):
                st.session_state.answers[current_q] = selected
                st.session_state.current_q += 1
                st.rerun()
        else:
            if st.button("추천 결과 보기", width="stretch", type="primary", disabled=(selected is None)):
                st.session_state.answers[current_q] = selected
                st.session_state.page = "result"
                st.rerun()
                
    st.divider()

    if st.button("테스트 취소하고 메인으로 돌아가기"):
        st.session_state.page = "main"
        st.session_state.current_q = 0
        st.session_state.answers = {}
        st.rerun()

# 결과 화면
elif st.session_state.page == "result":
    
    # 퀴즈 답변 분석 및 변환
    user_priority = ""
    user_foot_width = ""
    user_weight = ""
    user_ground = ""
    user_budget = ""
    
    for idx, q_item in enumerate(QUIZ_DATA):
        ans_text = st.session_state.answers.get(idx)
        if ans_text:
            for choice in q_item["choices"]:
                if choice["text"] == ans_text:
                    cat = q_item["category"]
                    if cat == "priority":
                          user_priority = choice["value"]
                    elif cat == "foot_width":
                          user_foot_width = choice["value"]
                    elif cat == "weight":
                          user_weight = choice["value"]
                    elif cat == "ground":
                          user_ground = choice["value"]
                    elif cat == "budget":
                          user_budget = choice["value"]
                    break

    payload = {
        "priority": user_priority,
        "foot_width": user_foot_width,
        "weight": user_weight,
        "ground": user_ground,
        "budget": user_budget
    }
    
    with st.spinner("FastAPI 추천 매핑 엔진이 작동 중"):
        try:
            response = requests.post(f"{BACKEND_URL}/recommend", json=payload, timeout=5)
            
            if response.status_code == 200:
                res_data = response.json()
                if res_data.get("success") and res_data.get("brand_recommendations"):
                    brand_recs = res_data["brand_recommendations"]
                    user_type = res_data["user_type"]
                    user_type_desc = res_data["user_type_desc"]
                    
                    st.write(f"### 메인 플레이 스타일: {user_type}")
                    st.write(user_type_desc)
                    
                    width_map = {"narrow": "칼발 (좁음)", "normal": "보통 발볼", "wide": "넓은 발볼"}
                    weight_map = {"light": "초경량 선호", "heavy": "묵직함 선호", "neutral": "상관없음 (보통)"}
                    ground_map = {"FG": "천연 잔디", "AG": "인조 잔디", "TF": "풋살장"}
                    budget_map = {"low": "15만원 미만", "mid": "15만원 ~ 25만원", "high": "25만원 이상"}

                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.write(f"- **발볼 타입**: {width_map.get(user_foot_width)}")
                        st.write(f"- **구장 종류**: {ground_map.get(user_ground)}")
                    with col_info2:
                        st.write(f"- **선호 무게**: {weight_map.get(user_weight)}")
                        st.write(f"- **예산 범위**: {budget_map.get(user_budget)}")
                    st.write("---")
                    
                    st.write("### 주요 브랜드별 최적 매칭 라인업")
                    
                    # 브랜드 탭 구성 (Nike, Adidas, Puma)
                    brand_names = ["Nike", "Adidas", "Puma"]
                    tabs = st.tabs(brand_names)
                    
                    for i, brand in enumerate(brand_names):
                        with tabs[i]:
                            cleat_data = brand_recs.get(brand)
                            if cleat_data:
                                st.write(f"#### {brand} 추천 모델: {cleat_data['name']}")
                                
                                # 매칭률 프로그레스 바
                                sim = cleat_data["similarity"]
                                st.write(f"- 매칭 적합도: **{sim}점** / 100점")
                                st.progress(sim / 100)
                                
                                st.write("##### 출시 등급 및 가격 정보")
                                recommended_grade = cleat_data.get("recommended_grade")
                                for grade_name, price_info in cleat_data["available_grades"].items():
                                    if grade_name == recommended_grade:
                                        st.write(f"- **{grade_name}**: {price_info} **(예산 부합 추천)**")
                                    else:
                                        st.write(f"- **{grade_name}**: {price_info}")
                                    
                                st.write("##### 모델 특성 설명")
                                st.write(cleat_data["description"])
                                
                            else:
                                st.write("해당 브랜드의 적절한 매칭 모델을 산출하지 못했습니다.")
                                
                else:
                    st.error("추천된 결과를 해독할 수 없습니다. 데이터베이스 응답이 비어 있습니다.")
            else:
                st.error(f"백엔드 연결 실패 (Status Code: {response.status_code})")
                st.info(f"대상 백엔드 URL: {BACKEND_URL}/recommend")
                
        except requests.exceptions.RequestException as e:
            st.error("FastAPI 백엔드 서버에 통신이 도달할 수 없습니다.")
            st.warning(f"서버 주소({BACKEND_URL})가 구동 중인지 터미널 docker ps를 확인해 주세요.")
            st.exception(e)

    st.divider()
    if st.button("다시 테스트하기", width="stretch"):
        st.session_state.page = "main"
        st.session_state.current_q = 0
        st.session_state.answers = {}
        st.rerun()
