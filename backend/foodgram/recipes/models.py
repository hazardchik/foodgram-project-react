from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import UniqueConstraint
from recipes import constants

User = get_user_model()

NAME_LIMIT = 150


class Ingredient(models.Model):
    name = models.CharField('Название', max_length=NAME_LIMIT)
    measurement_unit = models.CharField(
        'Единица измерения',
        max_length=NAME_LIMIT)

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ("name",)

    def __str__(self):
        return self.name


class Tags(models.Model):
    name = models.CharField(
        'Название', max_length=constants.RECIPE_NAME_AND_TAGS, unique=True
    )
    color = models.CharField(
        'Цветовой HEX-код', unique=True, max_length=constants.TAG_COLOR
    )
    slug = models.SlugField(
        'Слаг', unique=True, max_length=constants.RECIPE_NAME_AND_TAGS
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Recipes(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='автор',
        related_name='recipe'
    )
    name = models.CharField(
        'Название',
        max_length=NAME_LIMIT
    )
    image = models.ImageField(
        'Изображение рецепта',
        upload_to='recipes/images/'
    )
    text = models.TextField('Описание')
    cooking_time = models.PositiveSmallIntegerField(
        "Время приготовления",
        validators=[MinValueValidator(
            constants.COOKING_TIME_MIN,
            message="Время готовки должно быть не меньше чем 1 минута"
        ), MaxValueValidator(
            constants.COOKING_TIME_MAX,
            message=f"Время готовки должно"
                    f" быть меньше "
                    f"чем {constants.COOKING_TIME_MAX} минут"
        )]
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientInRecipe',
        verbose_name='Ингредиенты',
        related_name='recipes'
    )
    tags = models.ManyToManyField(
        Tags,
        verbose_name='Теги',
        related_name='recipe'
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ['-id']

    def __str__(self):
        return self.name


class IngredientInRecipe(models.Model):
    recipe = models.ForeignKey(
        Recipes,
        on_delete=models.CASCADE,
        related_name='ingredient_list'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE
    )
    amount = models.PositiveSmallIntegerField(
        "Количество ингредиента",
        validators=[
            MinValueValidator(constants.INGREDIENT_MIN_COUNT),
            MaxValueValidator(constants.INGREDIENT_MAX_COUNT)
        ],
    )

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'
        constraints = [
            UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='recipe_ingredient_unique'
            )
        ]

    def __str__(self):
        return f'{self.ingredient.name} {self.amount}'


class Favorite(models.Model):
    recipe = models.ForeignKey(
        Recipes,
        on_delete=models.CASCADE,
        verbose_name='Рецпет',
        related_name='favorite'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='favorite'
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        constraints = [
            UniqueConstraint(
                fields=('recipe', 'author'),
                name='unique_author_favorite'
            )
        ]

    def __str__(self):
        return f'{self.author} добавил {self.recipe} в избранное!'


class ShopCart(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shop',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipes,
        on_delete=models.CASCADE,
        related_name='shop',
        verbose_name='Рецепт'
    )

    class Meta:
        verbose_name = 'Корзина покупок'
        verbose_name_plural = 'Корзина покупок'
        constraints = [
            UniqueConstraint(
                fields=['author', 'recipe'],
                name='unique_shop_cart'
            )
        ]

    def __str__(self):
        return f'{self.author} добавил "{self.recipe}" в Корзину покупок.'
