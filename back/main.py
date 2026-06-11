from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict

# 추천 로직 가져오기
from recommendation import get_recommendations_by_brand

app = FastAPI(
    title="Soccer Cleats Simple Recommendation API",
    description="사용자의 플레이 스타일, 발볼 너비, 선호 무게감, 구장 환경, 예산 범위를 기반으로 최적의 축구화를 룰 기반 매칭해 주는 API",
    version="4.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 입력 스키마
class RecommendationRequest(BaseModel):
    priority: str = Field(..., description="가장 선호하는 스펙: speed, control, comfort")
    foot_width: str = Field(..., description="발볼 너비: narrow, normal, wide")
    weight: str = Field(..., description="선호 무게: light, heavy, neutral (하위 호환용 normal 허용)")
    ground: str = Field(..., description="주요 플레이 구장: FG, AG, TF")
    budget: str = Field(..., description="예산 범위: low, mid, high")

# 제품 스펙 스키마 (stats 정보 제외)
class BrandRecommendationItem(BaseModel):
    name: str
    description: str
    similarity: int
    available_grades: Dict[str, str]
    recommended_grade: str

class RecommendationResponse(BaseModel):
    success: bool
    user_type: str
    user_type_desc: str
    brand_recommendations: Dict[str, BrandRecommendationItem]

@app.get("/")
def read_root():
    return {"message": "축구화 추천 API 서버가 정상적으로 실행 중입니다."}

@app.post("/recommend", response_model=RecommendationResponse)
def recommend_cleats(request: RecommendationRequest):
    try:
        user_input = request.model_dump()
        
        # 룰 기반 매칭 서비스 호출
        results = get_recommendations_by_brand(user_input)
        
        return RecommendationResponse(
            success=True,
            user_type=results["user_type"],
            user_type_desc=results["user_type_desc"],
            brand_recommendations=results["brand_recommendations"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 연산 중 오류가 발생했습니다: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
