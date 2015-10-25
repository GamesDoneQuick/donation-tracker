# -*- coding: utf-8 -*-
from setuptools import setup
import os

setup(
    name='django-donation_tracker',
    version='2.1.1',
    author='Games Done Quick',
    author_email='donation_tracker@gamesdonequick.com',
    packages=['tracker', 'tracker.models', 'tracker.views', 'tracker.templatetags', 'tracker.migrations', 'tracker.south_migrations', 'tracker.tests'],
    url='https://github.com/GamesDoneQuick/donation-tracker',
    license='GPLv2',
    description='A Django app to assist in tracking donations for live broadcast events.',
    long_description=open('tracker/README.rst').read(),
    zip_safe=False,
    include_package_data=True,
    package_data={'tracker':
        ['%s/*.po' % os.path.relpath(a, 'tracker') for a,_,_ in os.walk('tracker/locale/')] +
        ['%s/*.png' % os.path.relpath(a, 'tracker') for a,_,_ in os.walk('tracker/static/')] +
        ['%s/*.js' % os.path.relpath(a, 'tracker') for a,_,_ in os.walk('tracker/static/')] +
        ['%s/*.css' % os.path.relpath(a, 'tracker') for a,_,_ in os.walk('tracker/static/')] +
        ['%s/*.html' % os.path.relpath(a, 'tracker') for a,_,_ in os.walk('tracker/templates/')] +
        ['README.rst']
        },
    install_requires=[
        'chromium-compact-language-detector',
        'Django>=1.8',
        'django-post-office',
        'django-ajax-selects',
        'django-mptt',
        'gdata',
        'oauth2client',
        'psycopg2',
        'python-dateutil',
        'pytz',
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Other Audience',
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
