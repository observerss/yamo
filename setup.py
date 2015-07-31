try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from yamo import __version__

setup(
    name='yamo',
    version=__version__,
    description='Yet Another MongoDB ORM',
    url='https://github.com/observerss/yamo',
    author='Jingchao Hu(observerss)',
    author_email='jingchaohu@gmail.com',
    packages=['yamo'],
    package_data={'': ['LICENSE']},
    license=open('LICENSE').read(),
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
