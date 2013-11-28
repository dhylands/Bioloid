from distutils.core import setup

setup(
    name='Bioloid',
    version='0.1.0',
    author='Dave Hylands',
    author_email='dhylands@gmail.com',
    packages=['bioloid'],
    scripts=[],
    url='http://pypi.python.org/pypi/Bioloid/',
    license='LICENSE.txt',
    description='Provides access to boiloid devices.',
    long_description=open('README.txt').read(),
    install_requires=[
        'pyyaml',
        'pyserial'
    ],
)
