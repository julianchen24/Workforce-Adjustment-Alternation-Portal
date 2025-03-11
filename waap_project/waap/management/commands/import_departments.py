import json
from django.core.management.base import BaseCommand
from waap.models import Department

class Command(BaseCommand):
    help = 'Import departments from a JSON file'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to the JSON file containing departments')

    def handle(self, *args, **options):
        json_file = options['json_file']
        
        try:
            with open(json_file, 'r') as f:
                departments_data = json.load(f)
            
            # Count of departments before import
            initial_count = Department.objects.count()
            
            # Import departments
            for dept_data in departments_data:
                name = dept_data.get('name')
                if name:
                    Department.objects.get_or_create(name=name)
            
            # Count of departments after import
            final_count = Department.objects.count()
            new_count = final_count - initial_count
            
            self.stdout.write(self.style.SUCCESS(f'Successfully imported {new_count} new departments. Total departments: {final_count}'))
            
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File not found: {json_file}'))
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f'Invalid JSON format in file: {json_file}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error importing departments: {str(e)}'))
