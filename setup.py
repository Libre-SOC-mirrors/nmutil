from setuptools import setup, find_packages
import sys, os

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
NEWS = open(os.path.join(here, 'NEWS.txt')).read()

version = '0.0.1'

install_requires = [
    'pyvcd',  # for stylish GTKWave documents - available on Pypi
]

test_requires = [
    'nose',
]

setup(
    name='nmutil',
    version=version,
    description="A nmigen utility library",
    long_description=README + '\n\n' + NEWS,
    classifiers=[
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: LGPLv3+",
        "Programming Language :: Python :: 3",
    ],
    keywords='nmigen utilities',
    author='Luke Kenneth Casson Leighton',
    author_email='lkcl@libre-riscv.org',
    url='http://git.libre-riscv.org/?p=nmutil',
    license='LGPLv3+',
    packages=find_packages('src'),
    package_dir = {'': 'src'},
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    tests_require=test_requires,
    test_suite='nose.collector',
)
