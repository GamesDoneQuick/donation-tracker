import os
import sys
from django.core.management import execute_from_command_line
sys.path.insert(0, os.path.join(os.getcwd(), 'tracker'))

execute_from_command_line(['circle_tests.py', 'test', 'tracker'])

