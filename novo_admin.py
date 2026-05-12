import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings') # Ajuste para o nome da sua pasta de settings
django.setup()

from django.contrib.auth.models import User
from core.models import Perfil # Ajuste para o nome do seu app

username = 'admin'
password = '123456789'

if not User.objects.filter(username=username).exists():
    user = User.objects.create_superuser(username, 'admin@email.com', password)
    perfil, _ = Perfil.objects.get_or_create(user=user)
    perfil.tipo_acesso = 'MASTER'
    perfil.save()
    print(f"Usuário {username} criado com sucesso e promovido a MASTER!")
else:
    print("Usuário já existe.")