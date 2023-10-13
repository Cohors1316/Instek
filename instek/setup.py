from setuptools import setup, find_packages

setup(
    name='instek',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        "pyserial",
    ],
    # entry_points={
    #     'console_scripts': [
    #         'instek=instek.cli:main',
    #     ],
    # },
    author='Ben Jordan',
    author_email='ben@poecoh.com',
    description='Simple utility for controlling Instek power supplies',
    url='https://github.com/cohors1316/instek',
)
