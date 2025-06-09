# common/views.py – 통합 로그인·회원가입(auth_portal) + 기타 페이지

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect

from .forms import UserForm  # signup용

# ────────────────────────────────────────────
# 1.  통합 로그인 · 회원가입 포털
# ────────────────────────────────────────────

# common/views.py

# common/views.py

# common/views.py

# views.py

from django.contrib.auth import login as auth_login
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.template.loader import render_to_string
from django.contrib.auth.models import User

from .forms import UserForm  # signup form


def auth_portal(request):
    """
    /common/auth/  – 로그인·회원가입 슬라이딩 UI 한 페이지
    prefix="signup" / prefix="login" 으로 어떤 폼을 바인딩할지 구분합니다.
    """
    # POST 가 아닐 때, 혹은 제출되지 않은 쪽은 빈 폼으로 생성
    if request.method == "POST" and "signup-username" in request.POST:
        signup_form = UserForm(request.POST, prefix="signup")
    else:
        signup_form = UserForm(prefix="signup")

    if request.method == "POST" and "login-username" in request.POST:
        login_form = AuthenticationForm(request, data=request.POST, prefix="login")
    else:
        login_form = AuthenticationForm(prefix="login")

    # 회원가입 처리
    if request.method == "POST" and "signup-username" in request.POST:
        if signup_form.is_valid():
            user = signup_form.save(commit=False)
            user.is_active = False
            user.save()

            uid   = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            current_site    = get_current_site(request)
            activation_path = reverse('common:activate', args=[uid, token])
            activation_link = request.build_absolute_uri(activation_path)

            subject = "이메일 인증을 완료해 주세요"
            message = render_to_string(
                'common/activation_email.html',
                {'user': user, 'activation_link': activation_link}
            )
            user.email_user(subject=subject, message=message)

            messages.success(
                request,
                "인증 메일을 발송했습니다. 메일함을 확인하고 링크를 클릭해 주세요."
            )
            return redirect("common:auth_portal")

    # 로그인 처리
    elif request.method == "POST" and "login-username" in request.POST:
        if login_form.is_valid():
            auth_login(request, login_form.get_user())
            messages.success(request, "로그인에 성공했습니다.")
            return redirect("pybo:main")

    # GET 또는 검증 실패 시
    return render(
        request,
        "common/auth.html",
        {"login_form": login_form, "signup_form": signup_form},
    )



def activate(request, uidb64, token):
    """회원 이메일 인증 처리"""
    try:
        uid  = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "이메일 인증이 완료되었습니다. 로그인해 주세요.")
    else:
        messages.error(request, "유효하지 않은 인증 링크입니다.")
    return redirect("common:auth_portal")

# ────────────────────────────────────────────
# 2.  로그아웃 뷰
# ────────────────────────────────────────────

def logout_view(request):
    """/common/logout/  – 세션 종료 후 메인으로"""
    auth_logout(request)
    messages.success(request, "로그아웃 되었습니다.")
    return redirect("common:auth_portal")


# ────────────────────────────────────────────
# 3.  기존 개별 로그인 · 회원가입 URL 호환 (선택)
#     → 모두 통합 페이지로 리다이렉트
# ────────────────────────────────────────────

def login_view(request):
    return redirect("common:auth_portal")

def signup(request):
    return redirect("common:auth_portal")


# ────────────────────────────────────────────
# 4.  기타 기능 페이지 데모
# ────────────────────────────────────────────

def photo_analysis(request):
    return render(request, "site1/photo_analysis.html")

def text_analysis(request):
    return render(request, "site1/text_analysis.html")

def book_search(request):
    return render(request, "site1/book_search.html")
