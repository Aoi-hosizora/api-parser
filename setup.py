from setuptools import setup

setup(
    name='apiparser',
    version='1.0.0',
    description='a command tool for rest api to generating swagger2 and apib document',
    author='Aoi-hosizora',
    url='https://github.com/Aoi-hosizora/api-parser',
    packages=['parser'],
    entry_points={
        'console_scripts': ['parser = parser.cli:main']
    },
    install_requires=[
        'PyYAML',
        'jsonref'
    ]
)
