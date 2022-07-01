from django.conf import settings
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action, api_view
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.response import Response


from .serializers import (UserSelfSerializer,
                          UserSerializer,
                          UserSignUpSerializer
                          )
from .services import generate_token, check_token
from .permissions import AdminOrSuperUser

User = get_user_model()


@api_view(['POST'])
def sign_up(request):
    """View-функция для создания нового пользователя
    и отправки ему на почту кода подтверждения."""
    serializer = UserSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data['email']
    username = serializer.validated_data['username']
    user, create = User.objects.get_or_create(
        username=username,
        email=email
    )
    confirmation_code = generate_token(user)
    user.save()
    send_mail(
        subject='Yamdb confirmation code',
        message=f'Ваш код подтверждения: {confirmation_code}',
        from_email=settings.AUTH_EMAIL,
        recipient_list=[user.email]
    )
    return Response(
        serializer.data,
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
def retrieve_token(request):
    """View-функция для получения JWT-токена по коду подтверждения
    и регистрации пользователя"""
    serializer = UserSignUpSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    if serializer.is_valid(raise_exception=True):
        user = get_object_or_404(User, username=request.data.get('username'))
        if check_token(user, request.data.get('confirmation_code')):
            access = AccessToken.for_user(user)
            return Response(
                {
                    'token': str(access)
                },
                status=status.HTTP_200_OK
            )
        return Response(
            {
                'confirmation_code': 'Confirmation code is invalid'
            },
            status=status.HTTP_400_BAD_REQUEST
        )


class UsersViewSet(viewsets.ModelViewSet):
    """Вьюсет для объектов модели User."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AdminOrSuperUser]
    lookup_field = 'username'
    pagination_class = PageNumberPagination

    @action(
        detail=False,
        methods=['get', 'patch'],
        permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        user = request.user
        serializer_class = UserSelfSerializer

        if request.method == 'GET':
            serializer = serializer_class(user)
            return Response(serializer.data)

        serializer = serializer_class(user, partial=True, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors)
