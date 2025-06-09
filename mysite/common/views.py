# common/views.py – 통합 로그인·회원가입(auth_portal) + 기타 페이지

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect

from .forms import UserForm  # signup용

# ────────────────────────────────────────────
# 1.  통합 로그인 · 회원가입 포털
# ────────────────────────────────────────────

def auth_portal(request):
    """/common/auth/  – 로그인·회원가입 슬라이딩 UI 한 페이지"""

    # 로그인용, 회원가입용 폼 인스턴스 준비
    login_form  = AuthenticationForm(request, data=request.POST or None, prefix="login")
    signup_form = UserForm(request.POST or None, prefix="signup")

    if request.method == "POST":
        # ── 회원가입 POST ─────────────────────
        if "signup-username" in request.POST:
            if signup_form.is_valid():
                signup_form.save()
                messages.success(request, "회원가입이 완료되었습니다. 이제 로그인해 주세요!")
                return redirect("common:auth_portal")

        # ── 로그인 POST ───────────────────────
        elif "login-username" in request.POST:
            if login_form.is_valid():
                auth_login(request, login_form.get_user())
                messages.success(request, "로그인에 성공했습니다.")
                return redirect("pybo:main")

    # GET 또는 검증 실패 → 템플릿 렌더
    return render(
        request,
        "common/auth.html",
        {"login_form": login_form, "signup_form": signup_form},
    )


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
