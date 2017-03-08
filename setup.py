from setuptools import setup, find_packages
import sys

if sys.version_info < (3, 5):
  sys.exit('Python < 3.5 is not supported')

setup(
  name='hvapi',
  version='0.1',
  description='Hyper-V python library.',
  author='Eugene Chekanskiy',
  author_email='echekanskiy@gmail.com',
  license='AS IS',
  packages=find_packages(),
  include_package_data=True
)
