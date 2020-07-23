"""Setup file for r3 package."""
from setuptools import setup

setup(
    name='r3',
    version='1.0.0',
    author='Patrick Wang',
    author_email='patrick@covar.com',
    url='https://github.com/patrickkwang/r3',
    description='Redis-REST with referencing',
    packages=['r3'],
    include_package_data=True,
    zip_safe=False,
    license='MIT',
    python_requires='>=3.8',
)
