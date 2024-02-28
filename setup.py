from setuptools import setup, find_packages

with open('README.rst', 'r') as file:
    long_description = file.read()

setup(
    name='css-resolver',
    version='0.0.1',
    long_description = long_description,
    long_description_content_type='text/x-rst',
    packages=find_packages(),
    install_requires=[
        'requests',
        'argparse',
        'colorama',
        'beautifulsoup4'
    ],
)
