import base64
from django.core.files.base import ContentFile
from rest_framework import serializers
from django.core.validators import MinValueValidator
from djoser.serializers import (
    TokenCreateSerializer,
    UserCreateSerializer as BaseUserCreateSerializer
)

from users.models import User
from .models import (Ingredient, RecipeIngredient, Recipe,
                     Tag, ShoppingCart, Favorite, Subscription
                     )


class UserCreateSerializer(BaseUserCreateSerializer):
    username = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)

    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = ('email', 'password', 'username', 'first_name', 'last_name')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        source='ingredient',
        queryset=Ingredient.objects.all()
    )
    name = serializers.CharField(
        source='ingredient.name',
        read_only=True
    )
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(
                base64.b64decode(imgstr),
                name=f'image.{ext}'
            )
        return super().to_internal_value(data)


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False, allow_null=True)
    shopping_cart_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email',
            'first_name', 'last_name',
            'is_subscribed', 'avatar', 'shopping_cart_count'
        )
        read_only_fields = ('id',)

    def get_avatar(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                user=request.user,
                author=obj
            ).exists()
        return False

    def get_shopping_cart_count(self, obj):
        return obj.shopping_cart_count


class RecipeReadSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True)
    ingredients = RecipeIngredientSerializer(
        many=True,
        source='ingredients_amounts'
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    cart_count = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'name', 'image', 'text',
            'ingredients', 'tags', 'cooking_time',
            'is_favorited', 'is_in_shopping_cart', 'cart_count'
        )
        read_only_fields = ('id', 'author')

    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(
                user=request.user,
                recipe=obj
            ).exists()
        return False

    def get_cart_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return ShoppingCart.objects.filter(user=request.user).count()
        return 0

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.in_carts.filter(user=request.user).exists()
        return False


class RecipeWriteSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
    image = Base64ImageField(required=True, max_length=None)
    cooking_time = serializers.IntegerField(
        validators=[MinValueValidator(
            1, message='Время должно быть не менее 1 минуты')]
    )

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'image', 'text',
            'ingredients', 'tags', 'cooking_time'
        )
        read_only_fields = ('id',)

    def _validate_ingredients_data(self, ingredients_data):
        if len(ingredients_data) == 0:
            raise serializers.ValidationError({
                'ingredients': 'Добавьте хотя бы один ингредиент'
            })

        ingredients = [item['ingredient'] for item in ingredients_data]
        if len(ingredients) != len(set(ingredients)):
            raise serializers.ValidationError({
                'ingredients': 'Ингредиенты не должны повторяться'
            })

        for item in ingredients_data:
            if item['amount'] <= 0:
                raise serializers.ValidationError({
                    'ingredients': f'Количество должно'
                    f'{item["ingredient"].name} быть больше нуля'
                })

    def _validate_tags_data(self, tags_data):
        if len(tags_data) == 0:
            raise serializers.ValidationError({
                'tags': 'Добавьте хотя бы один тег'
            })

        if len(tags_data) != len(set(tags_data)):
            raise serializers.ValidationError({
                'tags': 'Теги должны быть уникальными'
            })

    def _create_recipe_ingredients(self, recipe, ingredients_data):
        recipe_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient_data['ingredient'],
                amount=ingredient_data['amount']
            )
            for ingredient_data in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        self._validate_ingredients_data(ingredients_data)
        self._validate_tags_data(tags_data)
        image = validated_data.pop('image')
        recipe = Recipe.objects.create(
            image=image,
            **validated_data
        )
        recipe.tags.set(tags_data)
        self._create_recipe_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        if 'ingredients' in validated_data:
            ingredients_data = validated_data['ingredients']
            self._validate_ingredients_data(ingredients_data)
        if 'tags' in validated_data:
            tags_data = validated_data['tags']
            self._validate_tags_data(tags_data)
        if 'image' in validated_data:
            instance.image = validated_data.pop('image')
        if 'ingredients' in validated_data:
            RecipeIngredient.objects.filter(recipe=instance).delete()
            ingredients_data = validated_data.pop('ingredients')
            self._create_recipe_ingredients(instance, ingredients_data)
        if 'tags' in validated_data:
            tags_data = validated_data.pop('tags')
            instance.tags.set(tags_data)
        simple_fields = ['name', 'text', 'cooking_time']
        for field in simple_fields:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        instance.save()
        return instance


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ('user', 'recipe')
        read_only_fields = ('user',)

    def to_representation(self, instance):
        return ShortRecipeSerializer(
            instance.recipe,
            context=self.context
        ).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    cart_count = serializers.SerializerMethodField()

    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe', 'cart_count')
        read_only_fields = ('user',)

    def get_cart_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return ShoppingCart.objects.filter(user=request.user).count()
        else:
            return len(request.session.get('shopping_cart', []))


class SubscriptionSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(read_only=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count', 'avatar'
        )

    def get_recipes(self, obj):
        recipes_limit = self.context.get('recipes_limit')
        if recipes_limit:
            try:
                recipes_limit = int(recipes_limit)
                recipes = obj.recipes.all()[:recipes_limit]
            except ValueError:
                recipes = obj.recipes.all()
        else:
            recipes = obj.recipes.all()

        return ShortRecipeSerializer(
            recipes,
            many=True,
            context=self.context
        ).data

    def get_is_subscribed(self, obj):
        return True


class ShortRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = fields


class EmailTokenCreateSerializer(TokenCreateSerializer):

    def validate(self, attrs):
        email = attrs.get('email')
        try:
            user = User.objects.get(email=email)
            attrs['username'] = user.username
        except User.DoesNotExist:
            attrs['username'] = email

        return super().validate(attrs)
