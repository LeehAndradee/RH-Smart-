#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def sanitize_env():
    """Limpa variáveis de ambiente com caracteres inválidos para o psycopg2."""
    for key, value in list(os.environ.items()):
        try:
            # Tenta codificar o valor em UTF-8
            value.encode('utf-8')
        except UnicodeEncodeError:
            # Se falhar (ex: tem um 'ç' mal formatado no Windows), remove a variável
            # apenas para a execução deste processo
            del os.environ[key]
    
    # Força o Python a usar UTF-8 para o ambiente
    os.environ['PYTHONUTF8'] = '1'

def main():
    """Run administrative tasks."""
    # Chamamos a limpeza antes de qualquer coisa do Django
    sanitize_env()

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rhsmart.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()