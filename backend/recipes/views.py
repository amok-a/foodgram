from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import (
    viewsets, status, filters, permissions
)
from django.db.models import Count
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import JSONParser

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
from .filters import RecipeFilter
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
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = Pagination
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post', 'delete'],
            permission_classes=[permissions.IsAuthenticated])
    def avatar(self, request):
        user = request.user

        if request.method == 'POST':
            avatar = request.FILES.get('avatar')
            if not avatar:
                return Response(
                    {'error': 'Файл аватарки не предоставлен'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.avatar = avatar
            user.save()
            serializer = self.get_serializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)

        elif request.method == 'DELETE':

            if user.avatar:
                user.avatar.delete()
                user.avatar = None
                user.save()

            return Response(
                {'message': 'Аватарка успешно удалена'},
                status=status.HTTP_204_NO_CONTENT
            )
        else:
            return Response(
                {'error': 'У пользователя нет аватарки'},
                status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request, pk=None):
        author = get_object_or_404(User, id=pk)
        user = request.user
        if request.method == 'POST':
            serializer = SubscriptionSerializer(
                author,
                data={},
                context=self.get_serializer_context()
            )
            serializer.is_valid(raise_exception=True)

            Subscription.objects.create(user=user, author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:  # DELETE
            deleted_count, _ = Subscription.objects.filter(
                user=user, author=author).delete()
            if deleted_count == 0:
                return Response(
                    {'error': 'Вы не подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'],
            permission_classes=[permissions.IsAuthenticated])
    def subscriptions(self, request):
        queryset = User.objects.filter(
            following__user=request.user
        ).prefetch_related('recipes')
        recipes_limit = request.query_params.get('recipes_limit')
        context = self.get_serializer_context()
        if recipes_limit and recipes_limit.isdigit():
            context['recipes_limit'] = int(recipes_limit)
        page = self.paginate_queryset(queryset)
        serializer = SubscriptionSerializer(
            page, many=True, context=context)
        return self.get_paginated_response(serializer.data)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = [filters.SearchFilter]
    search_fields = ['^name']


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
