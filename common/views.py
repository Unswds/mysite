# common/views.py
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.shortcuts import render, redirect
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model

from .forms import UserForm, LoginForm

User = get_user_model()

# ───────────────────────────────────────────
# 1.  통합 로그인 · 회원가입 포털
# ───────────────────────────────────────────
def auth_portal(request):
    """ /common/auth/ – 한 페이지에서 로그인·회원가입 핸들링 """

    # 두 폼 인스턴스 (POST 여부와 관계없이 미리)
    signup_form = UserForm(request.POST or None, prefix="signup")
    login_form  = LoginForm(request, data=request.POST or None, prefix="login")

    # ───────── 회원가입 ─────────
    if request.method == "POST" and "signup-username" in request.POST:
        if signup_form.is_valid():
            user = signup_form.save(commit=False)   # pw 해싱 + is_active=False
            user.save()

            # 이메일 인증 링크 발송
            uid   = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            activation_link = request.build_absolute_uri(
                reverse("common:activate", args=[uid, token])
            )

            subject = "이메일 인증을 완료해 주세요"
            message = render_to_string(
                "common/activation_email.html",
                {"user": user, "activation_link": activation_link},
            )

            try:
                user.email_user(subject, message)
                messages.success(request, "인증 메일을 발송했습니다. 메일함을 확인해 주세요.")
            except Exception as e:
                messages.warning(
                    request,
                    f"회원가입은 완료되었지만 메일 발송에 실패했습니다: {e}",
                )

            return redirect("common:auth_portal")

    # ───────── 로그인 ─────────
    if request.method == "POST" and "login-username" in request.POST:
        username = request.POST.get("login-username")
        password = request.POST.get("login-password")

        # 1) inactive 계정인지 직접 먼저 검사
        user = User.objects.filter(username=username).first()
        if user and user.check_password(password) and not user.is_active:
            messages.error(request, "이메일이 인증되지 않았습니다.")
        else:
            # 2) 그 외의 경우는 LoginForm 정상 검증
            login_form  = LoginForm(request, data=request.POST, prefix="login")
            signup_form = UserForm(prefix="signup")   # 빈 폼으로 교체

            if login_form.is_valid():          # 여기까지 오면 비번 일치 & active
                user = login_form.get_user()
                auth_login(request, user)
                messages.success(request, "로그인에 성공했습니다.")
                return redirect("pybo:main")

            # 폼 전역 오류(아이디 미가입 등) 메시지
            for err in login_form.non_field_errors():
                messages.error(request, err)

    # ───────── GET 또는 검증 실패 ─────────
    return render(
        request,
        "common/auth.html",
        {"signup_form": signup_form, "login_form": login_form},
    )

# ───────────────────────────────────────────
# 2.  이메일 인증 링크 처리
# ───────────────────────────────────────────
def activate(request, uidb64, token):
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

# ───────────────────────────────────────────
# 3.  로그아웃
# ───────────────────────────────────────────
def logout_view(request):
    auth_logout(request)
    messages.success(request, "로그아웃 되었습니다.")
    return redirect("common:auth_portal")

# ───────────────────────────────────────────
# 4.  구 URL 호환
# ───────────────────────────────────────────
def login_view(request):
    return redirect("common:auth_portal")

def signup(request):
    return redirect("common:auth_portal")

# ───────────────────────────────────────────
# 5.  기타 데모 페이지
# ───────────────────────────────────────────
def photo_analysis(request):
    return render(request, "site1/photo_analysis.html")

def text_analysis(request):
    return render(request, "site1/text_analysis.html")

def book_search(request):
    return render(request, "site1/book_search.html")
