# from django.urls import path
# from django.contrib.auth import views as auth_views
# from . import views

# app_name = 'common'

# urlpatterns = [
#     # 로그인 페이지
#     path('', auth_views.LoginView.as_view(template_name='common/login.html'), name='login'),
#     path('signup/', views.signup, name='signup'),
#     path('logout/', auth_views.LogoutView.as_view(), name='logout'),
#     # pybo 페이지 클릭 시 로그인 화면으로 리디렉션
#     path('pybo/', auth_views.LoginView.as_view(template_name='common/login.html'), name='pybo_login'),
# ]

from django.urls import path
from . import views

app_name = 'common'

urlpatterns = [
    path('', views.login_view, name='login'),  # 커스텀 로그인
    path('auth/',  views.auth_portal,   name='auth_portal'),  # 우리의 새 페이지
    path('logout/', views.logout_view, name='logout'),
    path('photo-analysis/', views.photo_analysis, name='photo_analysis'),
    path('book_search/',    views.book_search,    name='book_search'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
]
