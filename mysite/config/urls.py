from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from common import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # ③ 책 찾아보기만 /pybo/book_search/ 으로 라우팅
    path(
        'pybo/',
        include(
            ('pybo.urls', 'pybo'),   # (모듈 경로, app_name)
            namespace='pybo'          # 네임스페이스 지정
        )
    ),

    # ④ 로그인/로그아웃/회원가입 (common 네임스페이스)
    path(
        'common/',
        include(
            ('common.urls', 'common'),
            namespace='common'
        )
    ),
    path('', lambda request: redirect('pybo:main')),  # ✅ 루트 URL은 pybo 메인 페이지로 리디렉션
    path('photo-analysis/', views.photo_analysis, name='photo_analysis'),
    path('text-analysis/',  views.text_analysis,  name='text_analysis'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
