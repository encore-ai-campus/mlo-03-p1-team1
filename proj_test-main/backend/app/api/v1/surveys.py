from fastapi import APIRouter, Depends
from app.api.deps import current_user
from app.schemas import SurveyInput, UserOut

router = APIRouter(prefix='/surveys', tags=['surveys'])


@router.put('/me', response_model=UserOut)
def save(data: SurveyInput, user=Depends(current_user)):
    user.categories = list(dict.fromkeys(data.categories))
    user.tags = data.tags
    user.preferences = data.preferences.model_dump()
    user.survey_completed = True
    return user
