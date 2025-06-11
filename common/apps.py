from django.apps import AppConfig

from django.apps import AppConfig
from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


class CommonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'common'

    def ready(self):
        # DEBUG 서버에서만 실행
        if settings.DEBUG:
            @receiver(user_logged_in)
            def _print_is_active(sender, user, request, **kwargs):
                print(
                    f"[DEBUG] login ▶ user='{user.username}'  is_active={user.is_active}"
                )