import base64
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.http import HttpResponse
from djoser.serializers import SetPasswordSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import (
    viewsets, status, filters, permissions
)
from django.db.models import Count
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser

from users.models import User
from .models import (
    Tag, Ingredient, Recipe,
    RecipeIngredient, Favorite, ShoppingCart, Subscription
)
from .serializers import (
    TagSerializer, IngredientSerializer, UserSerializer,
    RecipeReadSerializer, RecipeWriteSerializer,
    FavoriteSerializer, ShoppingCartSerializer,
    SubscriptionSerializer, UserCreateSerializer
)
from .pagination import Pagination
from .permissions import IsAuthorOrReadOnly
from .filters import RecipeFilter, IngredientFilter
import logging
from rest_framework.views import APIView
logger = logging.getLogger(__name__)


class UserCreateView(APIView):
    def post(self, request):
        logger.debug(f"UserCreateView: Received  {request.data}")
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            logger.debug(
                f"UserCreateView: Validated  {serializer.validated_data}")
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        logger.error(f"UserCreateView: Validation errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.annotate(recipes_count=Count('recipes'))
    serializer_class = UserSerializer
    pagination_class = Pagination
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return User.objects.annotate(recipes_count=Count('recipes'))

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'],
            permission_classes=[permissions.IsAuthenticated])
    def set_password(self, request):
        serializer = SetPasswordSerializer(
            data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            new_password = serializer.data.get("new_password")
            user.set_password(new_password)
            user.save()
            return Response({"status": "Пароль успешно изменен"},
                            status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['delete', 'put'],
            permission_classes=[permissions.IsAuthenticated],
            parser_classes=[MultiPartParser, FormParser, JSONParser])
    def avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            avatar_data = request.data.get('avatar')
            if avatar_data and str(avatar_data).strip():
                try:
                    base64_str = request.data['avatar']
                    if not base64_str.startswith('data:image'):
                        return Response(
                            {'error': 'Неверный формат."data:image"'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    format, imgstr = base64_str.split(';base64,')
                    ext = format.split('/')[-1]
                    file = ContentFile(
                        base64.b64decode(imgstr),
                        name=f'avatar.{ext}'
                    )
                    user.avatar.save(file.name, file, save=True)
                    return Response(
                        {'avatar': user.avatar.url}, status=status.HTTP_200_OK)

                except Exception as e:
                    return Response(
                        {'error': f'Ошибка обработки изображения: {str(e)}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                if user.avatar:
                    return Response(
                        {'avatar': user.avatar.url}, status=status.HTTP_200_OK)
                else:
                    return Response(
                        {'avatar': None}, status=status.HTTP_200_OK)

        elif request.method == 'DELETE':
            avatar_data = request.data.get('avatar')
            is_empty = (avatar_data is None
                        or avatar_data == ''
                        or avatar_data == 'null'
                        or (isinstance(avatar_data, str)
                            and not avatar_data.strip()))
            if is_empty:
                if user.avatar:
                    user.avatar.delete()
                    user.avatar = None
                    user.save()
                    logger.info("Avatar deleted by explicit request")
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                if user.avatar:
                    return Response(
                        {'avatar': user.avatar.url}, status=status.HTTP_200_OK)
                else:
                    return Response(
                        {'avatar': None}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request, author_id=None):
        author = get_object_or_404(User, id=author_id)
        user = request.user

        if request.method == 'POST':
            if user == author:
                return Response(
                    {'error': 'Нельзя подписаться на самого себя'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if Subscription.objects.filter(user=user, author=author).exists():
                return Response(
                    {'error': 'Вы уже подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            Subscription.objects.create(user=user, author=author)
            serializer = SubscriptionSerializer(
                author,
                context=self.get_serializer_context()
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            subscription = Subscription.objects.filter(
                user=user, author=author)
            if not subscription.exists():
                return Response(
                    {'error': 'Вы не подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'],
            permission_classes=[permissions.IsAuthenticated])
    def subscriptions(self, request):
        queryset = User.objects.filter(
            following__user=request.user
        ).annotate(recipes_count=Count('recipes')).prefetch_related('recipes')
        recipes_limit = request.query_params.get('recipes_limit')
        context = self.get_serializer_context()
        if recipes_limit and recipes_limit.isdigit():
            context['recipes_limit'] = int(recipes_limit)

        page = self.paginate_queryset(queryset)
        serializer = SubscriptionSerializer(
            page, many=True, context=context
        )
        return self.get_paginated_response(serializer.data)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    filterset_class = IngredientFilter
    search_fields = ['name']
    filterset_fields = {
        'name': ['exact', 'icontains', 'istartswith'],
    }


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.select_related('author').prefetch_related(
        'tags', 'ingredients_amounts__ingredient'
    )
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter
    permission_classes = [IsAuthorOrReadOnly]
    parser_classes = [JSONParser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        instance = serializer.instance
        read_serializer = RecipeReadSerializer(
            instance,
            context=self.get_serializer_context()
        )
        headers = self.get_success_headers(read_serializer.data)

        return Response(
            read_serializer.data, status=status.HTTP_201_CREATED,
            headers=headers)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=kwargs.pop('partial', False))
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        read_serializer = RecipeReadSerializer(
            instance,
            context=self.get_serializer_context()
        )

        return Response(read_serializer.data)

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def _favorite_shopping_action(
            self, request, pk, model, serializer_class, error_message):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user

        if request.method == 'POST':
            serializer = serializer_class(
                data={'user': user.id, 'recipe': recipe.id})
            serializer.is_valid(raise_exception=True)
            instance = model.objects.create(user=user, recipe=recipe)
            serializer = serializer_class(
                instance, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            deleted_count, _ = model.objects.filter(
                user=user, recipe=recipe).delete()
            if deleted_count == 0:
                return Response(
                    {'error': error_message['not_found']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'])
    def favorite(self, request, pk=None):
        return self._favorite_shopping_action(
            request, pk, Favorite, FavoriteSerializer, {
                'exists': 'Рецепт уже в избранном',
                'not_found': 'Рецепт не найден в избранном'
            }
        )

    @action(detail=True, methods=['post', 'delete'])
    def shopping_cart(self, request, pk=None):
        return self._favorite_shopping_action(
            request, pk, ShoppingCart, ShoppingCartSerializer, {
                'exists': 'Рецепт уже в списке покупок',
                'not_found': 'Рецепт не найден в списке покупок'
            }
        )

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(
                user=request.user,
                recipe=obj
            ).exists()
        return False

    @action(detail=False, methods=['get'])
    def shopping_cart_count(self, request):
        if request.user.is_authenticated:
            count = ShoppingCart.objects.filter(user=request.user).count()
            return Response({'count': count})
        return Response({'count': 0})

    @action(detail=False, methods=['get'])
    def download_shopping_cart(self, request):
        user = request.user
        if not user.shopping_cart.exists():
            return Response(
                {'error': 'Список покупок пуст'},
                status=status.HTTP_400_BAD_REQUEST
            )
        recipe_ids = user.shopping_cart.values_list('recipe_id', flat=True)
        ingredients = RecipeIngredient.objects.filter(
            recipe_id__in=recipe_ids
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(total_amount=Sum('amount'))

        content = "Список покупок:\n\n"
        for item in ingredients:
            content += (
                f"{item['ingredient__name']} - "
                f"{item['total_amount']} "
                f"{item['ingredient__measurement_unit']}\n"
            )

        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"')
        return response
