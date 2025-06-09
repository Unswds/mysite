from django.urls import path
from . import views

app_name = 'pybo'

urlpatterns = [
    path('', views.main, name='main'),                    # 메인 페이지
    path('generate/', views.generate_scenes, name='generate'),  # 이미지 생성 기능
    path('book_search/', views.book_search, name='book_search'),
    # 책 번호(idx)와 페이지 번호(page)를 받아서 렌더링
     # ─────────────────────────────────────────
    # ➊ /book/<idx>/ 요청 → book_detail 뷰에 page=1 디폴트로 넘겨주기
    path(
        'book/<int:idx>/',
        views.book_detail,
        {'page': 1},            # 기본 page 값 지정
        name='book_detail'      # name 을 기존과 동일하게 유지
    ),

    # ➋ /book/<idx>/<page>/ 요청 → book_detail 뷰에 idx, page 그대로 넘기기
    path(
        'book/<int:idx>/<int:page>/',
        views.book_detail,
        name='book_detail'
    ),
    path('photo_analysis/', views.photo_analysis, name='photo_analysis'),
    path("text-analysis/", views.text_analysis,  name="text_analysis"),
    path('api/analyze-text/', views.analyze_text,  name='analyze_text'),
]
