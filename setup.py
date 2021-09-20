"""Setup file for r3 package."""
from setuptools import setup

setup(
    name='NodeNormalization',
    version='2.0.1',
    author='Patrick Wang',
    author_email='patrick@covar.com',
    url='https://github.com/patrickkwang/r3',
    description='Takes a CURIE and returns the preferred CURIE for this entity',
    packages=[],
    include_package_data=True,
    zip_safe=False,
    license='MIT',
    python_requires='>=3.8',
)
