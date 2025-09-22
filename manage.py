#!/usr/bin/env python
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory_project.settings')
    try:
        from django.core.management import execute_from_command_line
    except Exception as exc:
        raise
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
