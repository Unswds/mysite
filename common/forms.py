from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

UserModel = get_user_model()


class UserForm(forms.ModelForm):
    """회원가입 폼

    - username · email · password1 · password2 필드 제공
    - 아이디·이메일 중복 검사
    - 비밀번호 일치 검사
    - save() 단계에서 비밀번호 해싱
    """

    username  = forms.CharField(max_length=150, label="아이디")
    email     = forms.EmailField(label="이메일")
    password1 = forms.CharField(widget=forms.PasswordInput, label="비밀번호")
    password2 = forms.CharField(widget=forms.PasswordInput, label="비밀번호 확인")

    class Meta:
        model  = User
        fields = ["username", "email", "password1", "password2"]

    # ──────────── 유효성 검증 ────────────
    def clean_email(self):
        email = self.cleaned_data.get("email")
        # 1) 도메인 체크
        domain = "@sasa.hs.kr"
        if not email.lower().endswith(domain):
            raise forms.ValidationError(f"이메일은 반드시 '{domain}' 도메인만 사용할 수 있습니다.")
        # 2) 중복 체크
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("이 이메일은 이미 사용 중입니다.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("이 사용자 이름은 이미 사용 중입니다.")
        return username

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "비밀번호가 일치하지 않습니다.")
        return cleaned
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.is_active = False       # 이메일 인증 전엔 비활성
        if commit:
            user.save()
        return user
    

class LoginForm(AuthenticationForm):
    """
    - 가입되지 않은 아이디  → “회원가입 해주세요!”
    - 이메일 미인증(is_active=False) → “이메일이 인증되지 않았습니다.”
    """

    username = forms.CharField(widget=forms.TextInput(attrs={
        "placeholder": "아이디",
        "class": "form-control",
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        "placeholder": "비밀번호",
        "class": "form-control",
    }))

    # 비밀번호는 맞았지만 is_active=False
    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError(
                _("이메일이 인증되지 않았습니다."),
                code="inactive",
            )

    # 아이디 존재 여부 검증
    def clean(self):
        try:
            return super().clean()

        except forms.ValidationError as e:
            username = self.data.get(self.add_prefix("username"), "")
            if username and not User.objects.filter(username=username).exists():
                raise forms.ValidationError(
                    _("회원가입 해주세요!"),
                    code="unregistered",
                ) from e
            raise