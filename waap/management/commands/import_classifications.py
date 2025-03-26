import json
from django.core.management.base import BaseCommand
from waap.models import Classification

class Command(BaseCommand):
    help = 'Import classifications from a JSON file'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to the JSON file containing classifications')

    def handle(self, *args, **options):
        json_file = options['json_file']
        
        try:
            with open(json_file, 'r') as f:
                classifications_data = json.load(f)
            
            # Count of classifications before import
            initial_count = Classification.objects.count()
            
            # Import classifications
            for class_data in classifications_data:
                code = class_data.get('code')
                name = class_data.get('name')
                if code and name:
                    Classification.objects.get_or_create(code=code, name=name)
            
            # Count of classifications after import
            final_count = Classification.objects.count()
            new_count = final_count - initial_count
            
            self.stdout.write(self.style.SUCCESS(f'Successfully imported {new_count} new classifications. Total classifications: {final_count}'))
            
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File not found: {json_file}'))
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f'Invalid JSON format in file: {json_file}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error importing classifications: {str(e)}'))
