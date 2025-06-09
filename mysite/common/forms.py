from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User


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

    # ──────────── 저장 로직 ────────────
    def save(self, commit: bool = True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])  # 해싱
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    """로그인 폼 – placeholder & 클래스만 살짝 커스터마이즈"""

    username = forms.CharField(widget=forms.TextInput(attrs={
        "placeholder": "아이디",
        "class": "form-control",
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        "placeholder": "비밀번호",
        "class": "form-control",
    }))
