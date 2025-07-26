from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import (
    viewsets, mixins, status, filters, permissions
)
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import JSONParser

from users.models import CustomUser
from .models import (
    Tag, Ingredient, Recipe,
    RecipeIngredient, Favorite, ShoppingCart, Subscription
)
from .serializers import (
    TagSerializer, IngredientSerializer, UserSerializer,
    RecipeReadSerializer, RecipeWriteSerializer,
    FavoriteSerializer, ShoppingCartSerializer,
    SubscriptionSerializer, CustomUserCreateSerializer
)
from .permissions import IsAuthorOrReadOnly
from .filters import RecipeFilter
import logging
from rest_framework.views import APIView
logger = logging.getLogger(__name__)

class UserCreateView(APIView):
    def post(self, request):
        logger.debug(f"UserCreateView: Received  {request.data}")
        serializer = CustomUserCreateSerializer(data=request.data)
        if serializer.is_valid():
            logger.debug(
                f"UserCreateView: Validated  {serializer.validated_data}")
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        logger.error(f"UserCreateView: Validation errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomPagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = 'limit'


class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    pagination_class = CustomPagination
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


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
    pagination_class = CustomPagination
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
            if model.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'error': error_message['exists']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            instance = model.objects.create(user=user, recipe=recipe)
            serializer = serializer_class(
                instance, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        instance = model.objects.filter(user=user, recipe=recipe)
        if not instance.exists():
            return Response(
                {'error': error_message['not_found']},
                status=status.HTTP_400_BAD_REQUEST
            )
        instance.delete()
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


class SubscriptionViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get_queryset(self):
        return CustomUser.objects.filter(
            following__user=self.request.user
        ).prefetch_related('recipes')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        recipes_limit = self.request.query_params.get('recipes_limit')
        if recipes_limit and recipes_limit.isdigit():
            context['recipes_limit'] = int(recipes_limit)
        return context

    def create(self, request, *args, **kwargs):
        author_id = kwargs.get('author_id')
        author = get_object_or_404(CustomUser, id=author_id)
        user = request.user

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
        serializer = self.get_serializer(
            author, context=self.get_serializer_context())
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        author_id = kwargs.get('author_id')
        author = get_object_or_404(CustomUser, id=author_id)
        user = request.user

        subscription = Subscription.objects.filter(user=user, author=author)
        if not subscription.exists():
            return Response(
                {'error': 'Вы не подписаны на этого пользователя'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(
            page, many=True, context=self.get_serializer_context())
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=['get'])
    def subscriptions(self, request):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
