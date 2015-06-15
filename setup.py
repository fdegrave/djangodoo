# -*- coding: utf-8 -*-
import os
from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='djangodoo',
    version='0.2.3',
    packages=['djangodoo'],
    include_package_data=True,
    license='MIT License',
    description='A Django app to copy models, load and save records from a running Odoo instance',
    long_description=README,
    url='https://github.com/fdegrave/djangodoo',
    author='François Degrave',
    author_email='francois.degrave@unamur.be',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Internet :: WWW/HTTP',
    ],
    install_requires=[
        "Django>=1.7.2",
        "ERPpeek>=1.6",
        "python-memcached"
    ],
    keywords=['Odoo', 'OpenERP', 'Django', ],
)
