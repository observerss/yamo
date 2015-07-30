try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import pathlib

root = pathlib.Path(__file__).parent.resolve()

setup(
    name='yamo',
    version='0.2.5',
    description='Yet Another MongoDB ORM',
    url='https://github.com/observerss/yamo',
    author='Jingchao Hu(observerss)',
    author_email='jingchaohu@gmail.com',
    packages=['yamo'],
    package_data={'': ['LICENSE']},
    license=(root / 'LICENSE').open().read(),
    install_requires=[
        'pymongo>=3',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
    ],
)
