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
        subprocess.check_call(['git', 'clean', '-fxd', 'tracker'])
        subprocess.check_call(['yarn'])
        subprocess.check_call(['yarn', 'build'])
        self.run_command('sdist')
        self.run_command('bdist_wheel')


def get_package_name(name):
    if not PACKAGE_NAME_SUFFIX:
        return name
    return f'{name}-{PACKAGE_NAME_SUFFIX}'


setup(
    name=get_package_name('django-donation-tracker'),
    version=json.load(open('package.json'))['version'],
    author='Games Done Quick',
    author_email='tracker@gamesdonequick.com',
    packages=find_packages(include=['tracker', 'tracker.*']),
    url='https://github.com/GamesDoneQuick/donation-tracker',
    license='Apache2',
    description='A Django app to assist in tracking donations for live broadcast events.',
    long_description=open('README.md').read(),
    zip_safe=False,
    # Included files are defined in MANIFEST.in, which will be automatically
    # picked up by setuptools.
    include_package_data=True,
    cmdclass={
        'package': PackageCommand,
    },
    install_requires=[
        'babel~=2.17.0',
        'celery~=5.0',
        'channels>=4.0',
        'Django>=4.2,<6.0',
        'django-ical~=1.7',
        'django-mptt~=0.10',
        'django-paypal~=1.1',
        'django-post-office~=3.2',
        'django-timezone-field>=7.0,<8.0',
        'djangorestframework~=3.9',
        'python-dateutil~=2.8.1;python_version<"3.11"',
        'requests>=2.27.1,<2.33.0',
    ],
    extras_require={
        'development': ['daphne~=4.0'],
        'tdqm': ['tqdm~=4.67.1'],
    },
    python_requires='>=3.9, <3.14',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Other Audience',
        'License :: OSI Approved :: Apache Software License 2.0 (Apache-2.0)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
