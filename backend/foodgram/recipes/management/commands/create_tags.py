from django.core.management.base import BaseCommand
from recipes.models import Tags


class Command(BaseCommand):
    """Загрузка данных в БД"""
    def handle(self, *args, **options):
        try:
            create_tags()
            print('теги созданы')
        except Exception as er:
            print(er)


def create_tags():
    Tags.objects.bulk_create([
        Tags(name='Завтрак', color='#ADFF2F', slug='breakfast'),
        Tags(name='Обед', color='#FFA500', slug='lunch'),
        Tags(name='Ужин', color='#F0E68C', slug='dinner')]
    )
