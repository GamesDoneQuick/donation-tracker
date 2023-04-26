# -*- coding: utf-8 -*-
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
    version='3.1',
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
        'backports.cached-property~=1.0.2;python_version<"3.8"',
        'celery~=5.0',
        'channels>=2.0',
        'Django>=3.2,!=4.0.*,<4.3',
        'django-ajax-selects~=2.2',
        'django-ical~=1.7',
        'django-mptt~=0.10',
        'django-paypal~=1.1',
        'django-post-office~=3.2',
        'django-timezone-field>=3.1,<6.0',
        'djangorestframework~=3.9',
        'python-dateutil~=2.8.1',
        'pytz>=2019.3',
        'requests>=2.27.1,<2.31.0',
    ],
    python_requires='>=3.7, <3.12',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Other Audience',
        'License :: OSI Approved :: Apache Software License 2.0 (Apache-2.0)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
