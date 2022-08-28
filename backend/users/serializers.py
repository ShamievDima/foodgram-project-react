from django.contrib.auth import get_user_model
from djoser.conf import settings
from djoser.serializers import (SetPasswordSerializer, UserCreateSerializer,
                                UserSerializer)

User = get_user_model()


class CustomUserSerializer(UserSerializer):
    class Meta:
        model = User
        fields = (settings.LOGIN_FIELD, settings.USER_ID_FIELD
                  ) + tuple(User.REQUIRED_FIELDS)
        read_only_fields = (settings.LOGIN_FIELD,)


class CustomUserCreateSerializer(UserCreateSerializer):

    class Meta:
        model = User
        fields = (settings.LOGIN_FIELD,
                  settings.USER_ID_FIELD,
                  "password",
                  ) + tuple(User.REQUIRED_FIELDS)


class CustomSetPasswordSerializer(SetPasswordSerializer):
    class Meta:
        fields = ('password',)
