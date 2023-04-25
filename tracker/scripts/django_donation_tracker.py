import os
import subprocess
import sys


def build():
    # Move out to the root of the package (from 'tracker/scripts')
    os.chdir(os.path.realpath(os.path.join(__file__, '..', '..')))
    # Install JS dependencies
    subprocess.check_call(['yarn'])
    # Build the JS bundles
    subprocess.check_call(['yarn', 'build'])

    print('Successfully installed and built JavaScript bundles')


def run(command):
    if command == 'build':
        build()


def as_cli():
    command = sys.argv[1]

    run(command)
