import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ponteglam.settings')
django.setup()

from django.apps import apps
from django.db import models

def get_model_structure():
    output = []
    # Apps del proyecto (excluyendo las de Django por defecto para simplicidad)
    project_apps = [
        'users', 'companies', 'headquarters', 'services', 
        'workers', 'notifications', 'transactions', 'ratings',
        'chats', 'blogs', 'reports', 'pqrs'
    ]
    
    for app_label in project_apps:
        try:
            app_config = apps.get_app_config(app_label)
            output.append(f"\n### APP: {app_label.upper()}")
            output.append("-" * 30)
            
            for model in app_config.get_models():
                model_name = model.__name__
                output.append(f"\n- **Modelo: {model_name}**")
                
                # Campos de relación
                relations = []
                for field in model._meta.get_fields():
                    if isinstance(field, (models.ForeignKey, models.OneToOneField, models.ManyToManyField)):
                        related_model = field.related_model.__name__ if field.related_model else "Self"
                        rel_type = type(field).__name__
                        relations.append(f"  - {field.name} ({rel_type}) -> {related_model}")
                
                if relations:
                    output.extend(relations)
                else:
                    output.append("  - (Sin relaciones directas)")
        except LookupError:
            continue
            
    return "\n".join(output)

if __name__ == "__main__":
    print(get_model_structure())
