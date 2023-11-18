from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.db import transaction
from djoser.serializers import UserCreateSerializer as DjoserUCreateSerializer
from djoser.serializers import UserSerializer as DjoserUserSerializer
from drf_extra_fields.fields import Base64ImageField
from recipes import constants
from recipes.models import Ingredient, IngredientInRecipe, Recipes, Tags
from rest_framework import serializers
from rest_framework.fields import IntegerField, SerializerMethodField
from rest_framework.relations import PrimaryKeyRelatedField
from users.models import Follow, User


class UserCreateSerializer(DjoserUCreateSerializer):

    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'password',)


class UsersSerializer(DjoserUserSerializer):
    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name',
                  'last_name', 'is_subscribed',)

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        return (request.user.is_authenticated
                and request.user.follower.filter(author=obj).exists())


class SubscribeSerializer(serializers.ModelSerializer):
    """Сериалайзер для вывода подписок пользователя."""

    class Meta:
        model = Follow
        fields = (
            "author",
            "user",
        )

    def validate(self, data):
        user = data.get("user")
        author = data.get("author")

        if Follow.objects.filter(user=user, author=author).exists():
            raise ValidationError(
                "Вы уже подписаны на этого автора"
            )
        if user == author:
            raise ValidationError(
                "Подписаться на самого себя невозможно",
                code=HTTPStatus.BAD_REQUEST,
            )
        return data


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tags
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit',)


class IngredientInRecipeReadSerializer(serializers.ModelSerializer):
    id = IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit')

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount',)


class RecipeReadSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True)
    ingredients = IngredientInRecipeReadSerializer(
        many=True, source='ingredient_list')
    author = UsersSerializer()
    image = Base64ImageField()
    is_favorited = SerializerMethodField(read_only=True)
    is_in_shopping_cart = SerializerMethodField(read_only=True)

    class Meta:
        model = Recipes
        fields = ('id', 'tags', 'author',
                  'ingredients', 'is_favorited',
                  'is_in_shopping_cart', 'image',
                  'name', 'text', 'cooking_time',)

    def get_is_favorited(self, obj):
        request = self.context.get("request")
        return (request.user.is_authenticated
                and obj.favorite.filter(user=request.user).exists())

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get("request")
        return (request.user.is_authenticated
                and obj.shop.filter(user=request.user).exists())


class IngredientInRecipeCreateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField(
        min_value=constants.INGREDIENT_MIN_COUNT,
        max_value=constants.INGREDIENT_MAX_COUNT,
        error_messages={
            "min_value": "Должно быть не меньше 1.",
            "max_value": "Превышено максимальное количество."
        }
    )

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'amount')


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = IngredientInRecipeCreateSerializer(many=True)
    tags = PrimaryKeyRelatedField(queryset=Tags.objects.all(), many=True)
    author = UsersSerializer(read_only=True)
    image = Base64ImageField()
    cooking_time = serializers.IntegerField(
        min_value=constants.COOKING_TIME_MIN,
        max_value=constants.COOKING_TIME_MAX
    )

    class Meta:
        model = Recipes
        fields = ('id', 'tags', 'author', 'ingredients',
                  'image', 'name', 'text', 'cooking_time',)

    def validate(self, data):
        ingredients = self.initial_data.get('ingredients')
        tags = self.initial_data.get('tags')
        ingredient_list = {ingredient["id"] for ingredient in ingredients}
        if len(ingredient_list) != len(ingredients):
            raise serializers.ValidationError(
                {'ingredients': "Ингредиенты не должны повторяться."}
            )
        if not ingredients:
            raise serializers.ValidationError(
                {"ingredients": "Нужно выбрать хотя бы один ингредиент!"}
            )
        if not tags:
            raise serializers.ValidationError(
                {'tags': 'Нужно выбрать хотя бы один тег!'})
        return data

    @staticmethod
    def create_ingredients_and_tags(recipe, tags, ingredients):
        recipe.tags.set(tags)
        ingredients_data = [
            IngredientInRecipe(
                recipe=recipe,
                ingredient=ingredient['id'],
                amount=ingredient['amount']
            ) for ingredient in ingredients
        ]
        IngredientInRecipe.objects.bulk_create(ingredients_data)

    @transaction.atomic
    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipes.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_ingredients_and_tags(recipe, tags, ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        instance = super().update(instance, validated_data)
        instance.tags.clear()
        instance.tags.set(tags)
        instance.ingredients.clear()
        self.create_ingredients_and_tags(instance, tags, ingredients)
        instance.save()
        return instance

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context={
            'request': self.context.get('request')
        }).data


class RecipeShortSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipes
        fields = ('id', 'name', 'image', 'cooking_time',)


class FollowSerializer(UsersSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UsersSerializer.Meta):
        fields = UsersSerializer.Meta.fields + ('recipes', 'recipes_count')
        read_only_fields = UsersSerializer.Meta.fields

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        queryset = obj.recipe.all()
        if limit:
            queryset = queryset[:int(limit)]
        return RecipeShortSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        return obj.recipe.count()
