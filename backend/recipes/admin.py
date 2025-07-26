from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django import forms
import json


from .models import (Tag, Ingredient, Recipe,
                     RecipeIngredient, Favorite, ShoppingCart)
from users.models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (("Personal info"), {"fields": ("first_name", "last_name",
                                        "email", "avatar")}),
        (("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser",
                                      "groups", "user_permissions")}),
        (("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username", "password1", "password2",
                "email", "first_name", "last_name"),
        }),
    )
    search_fields = ('username', 'email')


class RecipeForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        widget=admin.widgets.FilteredSelectMultiple('Tags', is_stacked=False),
        required=True,
    )

    ingredients = forms.ModelMultipleChoiceField(
        queryset=Ingredient.objects.all(),
        widget=admin.widgets.FilteredSelectMultiple(
            'Ингредиенты', is_stacked=False),
        required=True,
    )

    class Meta:
        model = Recipe
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].widget = forms.ClearableFileInput()

        if self.instance.pk:
            self.fields['tags'].initial = self.instance.tags.all()
            ingredient_ids = list(
                self.instance.ingredients_amounts.values_list('id', flat=True))
            self.fields['ingredients'].initial = ingredient_ids
            for ingredient in Ingredient.objects.all():
                field_name = f'ingredient_amount_{ingredient.id}'
                initial_value = 1
                try:
                    ri = RecipeIngredient.objects.get(
                        recipe=self.instance,
                        ingredient=ingredient
                    )
                    initial_value = ri.amount
                except RecipeIngredient.DoesNotExist:
                    pass

                self.fields[field_name] = forms.IntegerField(
                    label=f'{ingredient.name} ({ingredient.measurement_unit})',
                    initial=initial_value,
                    min_value=1,
                    required=False
                )

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:
            instance.save()

        if instance.pk:
            instance.tags.set(self.cleaned_data['tags'])
            instance.ingredients_amounts.all().delete()
            RecipeIngredient.objects.filter(recipe=instance).delete()
            for field_name, value in self.cleaned_data.items():
                if field_name.startswith('ingredient_amount_'):
                    ingredient_id = int(field_name.split('_')[-1])
                    if value and value > 0:
                        ingredient = Ingredient.objects.get(id=ingredient_id)
                        RecipeIngredient.objects.create(
                            recipe=instance,
                            ingredient=ingredient,
                            amount=value
                        )

        return instance


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    form = RecipeForm
    list_display = ('name', 'author', 'cooking_time')
    filter_horizontal = ('tags',)
    fieldsets = (
        (None, {
            'fields': ('name', 'author', 'text', 'image', 'cooking_time')
        }),
        ('Теги', {
            'fields': ('tags',),
        }),
        ('Статистика', {
            'fields': ('favorite_count',),
        }),
    )

    def favorite_count(self, obj):
        return obj.favorites.count()

    search_fields = ('name', 'author__username')
    list_filter = ('tags',)
    readonly_fields = ('favorite_count',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)
    actions = ['import_from_json']

    def import_from_json(self, request, queryset):
        with open('data/ingredients.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                Ingredient.objects.get_or_create(
                    name=item['name'],
                    measurement_unit=item['measurement_unit']
                )
        self.message_user(request, "Ингредиенты успешно загружены")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
