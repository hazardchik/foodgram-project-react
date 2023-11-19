from django.contrib import admin
from django.contrib.admin import display

from .models import (Favorite, Ingredient, IngredientInRecipe, Recipes,
                     ShopCart, Tags)


class RecipeIngredintInline(admin.TabularInline):
    model = IngredientInRecipe
    extra = 1
    min_num = 1


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    list_filter = ('name',)


@admin.register(Tags)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color')


@admin.register(Recipes)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', )
    list_filter = ('author', 'name', 'tags',)
    readonly_fields = ('added_to_favorite',)
    inlines = (RecipeIngredintInline, )

    @display(description='Добавлений в избранное')
    def added_to_favorite(self, obj):
        return obj.favorite.count()


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('author', 'recipe')


@admin.register(ShopCart)
class ShopCarteAdmin(admin.ModelAdmin):
    list_display = ('author', 'recipe')
