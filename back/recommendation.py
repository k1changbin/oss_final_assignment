from typing import Dict, Any
import re

# 외부 데이터 파일로부터 브랜드 데이터 가져오기
from cleat_data import CLEATS_DB

def parse_price(price_str: str) -> int:
    """
    숫자 문자열만 추출하여 정수로 변환
    "엘리트 FG (약 339,000원)" -> 339000
    "미출시" -> -1
    """
    if not price_str or "원" not in price_str:
        return -1
    
    # '약 XXX,XXX원' 혹은 'XXX,XXX원' 형식에서 가격 부분 숫자만 매칭 추출
    match = re.search(r'([\d,]+)\s*원', price_str)
    if match:
        digits = re.sub(r'[^\d]', '', match.group(1))
        if digits:
            return int(digits)
    return -1


def calculate_score(user_data: Dict[str, Any], cleat_info: Dict[str, Any], priority_key: str) -> int:
    """
    사용자의 입력 다차원 고려사항과 축구화 개별 속성을 비교하여 적합도 점수(0~100점)를 계산
    - 플레이스타일 매칭: 최대 40점
    - 발볼 너비 매칭: 최대 40점 (넓은 발볼 유저에게 칼발 축구화 추천 시 -30 페널티 적용)
    - 선호 무게감 매칭: 최대 20점 (상관없음 선택 시 15점 부여)
    """
    score = 0
    
    # 플레이스타일/우선가치 매칭 (최대 40점)
    if user_data["priority"] == priority_key:
        score += 40
    else:
        score += 10
        
    # 발볼 너비 매칭 (최대 40점)
    fit = cleat_info["fit"]
    u_width = user_data["foot_width"]
    
    # 발볼 압박 위험 (유저 발볼 넓음 & 축구화 칼발/narrow) 감점 페널티 플래그
    apply_width_penalty = False
    if u_width == "wide" and fit == "narrow":
        apply_width_penalty = True

    if u_width == fit:
        score += 40
    elif u_width == "normal" or fit == "normal":
        score += 30
    else: # narrow <-> wide 충돌 상황 (일반)
        score += 10
        
    # 무게 매칭 (최대 20점)
    c_weight = cleat_info["weight"]
    u_weight = user_data["weight"]
    
    if u_weight == "neutral":
        # 상관없음(보통) 선택 시 일괄 15점 부여하여 다른 요소가 영향력을 갖도록 유도
        score += 15
    elif u_weight == c_weight:
        # 정확히 일치 (light-light, heavy-heavy)
        score += 20
    elif (u_weight == "light" and c_weight == "normal") or (u_weight == "heavy" and c_weight == "normal"):
        # 인접 단계 (light-normal, heavy-normal)
        score += 12
    else:
        # 반대 극단 (light-heavy)
        score += 5
        
    # 페널티 감점 적용
    if apply_width_penalty:
        score -= 30
        
    # 점수 하한선 0점 보장
    if score < 0:
        score = 0
        
    return score

def get_recommendations_by_brand(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    사용자의 입력값들을 종합 채점하여 각 브랜드별로 가장 매칭 적합도가 높은 모델과 아웃솔을 산출
    """
    user_ground = user_data["ground"]

    type_labels = {
        "speed": "스피드 특화형 (Speed)",
        "control": "드리블 및 패스 컨트롤형 (Control)",
        "comfort": "착화감 및 발볼 편안함형 (Comfort)"
    }
    type_descs = {
        "speed": "폭발적인 직선 질주와 가속력을 통해 경기장을 파괴하는 스피드 성능을 우선순위로 삼습니다.",
        "control": "정밀한 퍼스트 터치와 킥 제어를 바탕으로 영리하게 드리블하고 빌드업 패스를 선호합니다.",
        "comfort": "발의 피로, 물집 방지 및 발볼 압박 해소를 통한 안정적이고 부드러운 착화감을 우선시합니다."
    }
    
    user_type = type_labels[user_data["priority"]]
    user_type_desc = type_descs[user_data["priority"]]

    brand_recommendations = {}
    brands = ["Nike", "Adidas", "Puma"]


    # 아래 fallback 및 "미출시" 로직은 향후 데이터 추가/변경 시를 대비한 안전장치(safety net)
    ground_fallback_order = {
        "FG": ["MG"],
        "AG": ["MG"],
        "TF": [],       # TF는 대체 구장 없음 (현재 데이터에서는 모든 모델에 TF 존재)
        "MG": ["AG", "FG"]
    }

    for brand in brands:
        best_silo_key = None
        best_score = -1
        best_cleat_info = None

        # 브랜드별 3대 실루엣 전체를 채점하여 가장 높은 적합도를 기록한 모델 선출
        for silo_key in ["speed", "control", "comfort"]:
            cleat_info = CLEATS_DB[brand][silo_key]
            score = calculate_score(user_data, cleat_info, silo_key)
            if score > best_score:
                best_score = score
                best_silo_key = silo_key
                best_cleat_info = cleat_info

        outsoles = best_cleat_info.get("outsoles", {})
        
        # 각 등급별로 현재 구장에 맞는 아웃솔 사양과 가격 정보 추출
        available_grades = {}
        grade_mapping = {
            "high": "고급형",
            "mid": "중급형"
        }
        
        for grade_key, grade_label in grade_mapping.items():
            if grade_key in outsoles:
                # 해당 등급에 선택한 구장 스펙이 바로 출시되었는지 확인
                if user_ground in outsoles[grade_key]:
                    available_grades[grade_label] = outsoles[grade_key][user_ground]
                else:
                    # 타 구장 스펙 호환/우회 검색 (Puma FG/AG -> MG 대체)
                    fallback_found = False
                    for alt_ground in ground_fallback_order.get(user_ground, []):
                        if alt_ground in outsoles[grade_key]:
                            available_grades[grade_label] = f"{outsoles[grade_key][alt_ground]} (대체 추천)"
                            fallback_found = True
                            break
                    if not fallback_found:
                        # 안전장치: 현재 데이터에서는 도달하지 않음
                        available_grades[grade_label] = "미출시"
            else:
                # 안전장치: 현재 데이터에서는 모든 모델에 high/mid 등급이 존재하므로 도달하지 않음
                available_grades[grade_label] = "미출시"

        # 사용자의 예산 범위(low/mid/high)에 맞는 최적 등급(recommended_grade) 산정
        user_budget = user_data.get("budget", "mid")
        high_price_str = available_grades.get("고급형")
        mid_price_str = available_grades.get("중급형")
        
        high_price = parse_price(high_price_str)
        mid_price = parse_price(mid_price_str)
        
        # 각 모델이 사용자의 예산 상한선 이하(구매 가능)인지 판별
        high_affordable = (high_price != -1) and (
            user_budget == "high" or
            (user_budget == "mid" and high_price < 250000) or
            (user_budget == "low" and high_price < 150000)
        )
        mid_affordable = (mid_price != -1) and (
            user_budget == "high" or
            (user_budget == "mid" and mid_price < 250000) or
            (user_budget == "low" and mid_price < 150000)
        )
        
        # 기본 추천 등급 설정 (둘 다 예산 초과 시 저렴한 중급형 기본 권장, 예산이 high인 경우 고급형 기본 권장)
        if user_budget == "high":
            default_grade = "고급형"
        else:
            default_grade = "중급형"
            
        recommended_grade = default_grade
        if user_budget == "high":
            # high 예산: 고급형 우선 추천
            if high_affordable:
                recommended_grade = "고급형"
            elif mid_affordable:
                recommended_grade = "중급형"
        elif user_budget == "mid":
            # mid 예산: 고급형을 살 수 있으면 고급형 추천, 고급형이 예산 초과면 중급형 추천
            if high_affordable:
                recommended_grade = "고급형"
            elif mid_affordable:
                recommended_grade = "중급형"
        elif user_budget == "low":
            # low 예산: 더 저렴한 중급형 우선 추천
            if mid_affordable:
                recommended_grade = "중급형"
            elif high_affordable:
                recommended_grade = "고급형"

        # 발볼 보정 추천 경고 안내문 추가 (사용자 선호 스타일과 다른 라인이 최선책으로 추천되었을 때)
        description_suffix = ""
        if best_silo_key != user_data["priority"]:
            style_ko = type_labels[user_data["priority"]].split("(")[0].strip()
            description_suffix = (
                f"\n\n 선호 스타일({style_ko}) 대비 발볼 압박 및 부상을 예방하기 위해, "
                f"발볼 설계가 더 넓고 편안한 '{type_labels[best_silo_key].split('(')[0].strip()}' 라인의 모델로 대체 추천되었습니다."
            )

        brand_recommendations[brand] = {
            "name": best_cleat_info["name"],
            "description": best_cleat_info["desc"] + description_suffix,
            "similarity": best_score,
            "available_grades": available_grades,
            "recommended_grade": recommended_grade
        }

    return {
        "success": True,
        "user_type": user_type,
        "user_type_desc": user_type_desc,
        "brand_recommendations": brand_recommendations
    }
