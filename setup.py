# -*- coding: utf-8 -*-
import json
import os
import subprocess

from setuptools import Command, find_packages, setup

PACKAGE_NAME_SUFFIX = os.environ.get('PACKAGE_NAME_SUFFIX', None)


class PackageCommand(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        # TODO: replace this with a script instead of being a custom command
        subprocess.check_call(['git', 'clean', '-fxd', 'tracker'])
        output = subprocess.check_output(['yarn', 'plugin', 'runtime', '--json'])
        if not any(
            json.loads(s).get('name', None) == '@yarnpkg/plugin-workspace-tools'
            for s in output.decode('utf-8').split('\n')
            if s
        ):
            subprocess.check_call(['yarn', 'plugin', 'import', 'workspace-tools'])
        subprocess.check_call(['yarn', 'workspaces', 'focus', '--production'])
        subprocess.check_call(['yarn', 'build'])
        # remove the plugin reference
        subprocess.check_call(['git', 'checkout', '.yarnrc.yml'])
        self.run_command('sdist')
        self.run_command('bdist_wheel')


setup(
    name='django-donation-tracker',
    packages=find_packages(include=['tracker', 'tracker.*']),
    url='https://github.com/GamesDoneQuick/donation-tracker',
    description='A Django app to assist in tracking donations for live broadcast events.',
    long_description=open('README.md').read(),
    zip_safe=False,
    # Included files are defined in MANIFEST.in, which will be automatically
    # picked up by setuptools.
    include_package_data=True,
    cmdclass={
        'package': PackageCommand,
    },
)
