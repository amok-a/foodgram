import os
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Load ingredients from JSON files in ../data/'

    def handle(self, *args, **options):
        base_dir = settings.BASE_DIR
        data_dir = os.path.join(base_dir.parent, 'data')

        json_path = os.path.join(data_dir, 'ingredients.json')
        if os.path.exists(json_path):
            self.load_json(json_path)

    def load_json(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            ingredients = []
            for item in data:
                ingredients.append(
                    Ingredient(
                        name=item['name'],
                        measurement_unit=item['measurement_unit']
                    )
                )
            Ingredient.objects.bulk_create(ingredients)
            self.stdout.write(self.style.SUCCESS(
                f'Loaded {len(ingredients)} ingredients from JSON'))
