# -*- coding: utf-8 -*-
import os

from setuptools import setup, find_packages, Command

import subprocess


class PackageCommand(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        subprocess.check_call(['git', 'clean', '-fxd', 'tracker'])
        subprocess.check_call(['yarn', '--production'])
        subprocess.check_call(['yarn', 'build'])
        self.run_command('sdist')
        self.run_command('bdist_wheel')


package_data = []

old_dir = os.getcwd()

os.chdir('tracker')

for path in ['templates', 'static', 'locale', 'fixtures']:
    for root, dirs, files in os.walk(path):
        for f in files:
            package_data.append(os.path.join(root, f))

os.chdir(old_dir)

setup(
    name='django-donation-tracker',
    version='3.0',
    author='Games Done Quick',
    author_email='tracker@gamesdonequick.com',
    packages=find_packages(include=['tracker', 'tracker.*']),
    url='https://github.com/GamesDoneQuick/donation-tracker',
    license='Apache2',
    description='A Django app to assist in tracking donations for live broadcast events.',
    long_description=open('README.md').read(),
    zip_safe=False,
    package_data={
        '': ['README.md'],
        'tracker': package_data + ['ui-tracker.manifest.json',],
    },
    cmdclass={'package': PackageCommand,},
    install_requires=[
        'celery~=5.0',
        'channels>=2.0',
        'Django>=2.2,!=3.0.0.a,!=3.1.0.a,<5.0',
        'django-ajax-selects~=1.9',
        'django-ical~=1.7',
        'django-mptt~=0.10',
        'django-paypal~=1.1',
        'django-post-office~=3.2',
        'django-timezone-field>=3.1,<5.0',
        'djangorestframework~=3.9',
        'python-dateutil~=2.8.1',
        'pytz>=2019.3',
        'webpack-manifest~=2.1',
    ],
    python_requires='>=3.6, <3.11',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Other Audience',
        'License :: OSI Approved :: Apache Software License 2.0 (Apache-2.0)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
