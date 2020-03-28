from setuptools import setup
from sys import version_info

setup(name='buver',
      version='0.8.8',
      description='BackUp Versioning for directory trees',
      url='https://github.com/kenlowrie/buver',
      author='Ken Lowrie',
      author_email='ken@kenlowrie.com',
      license='Apache',
      packages=['buver'],
      install_requires=['kenl380.pylib'],
      entry_points = {
        'console_scripts': ['buver=buver.buver:buver_entry',
                            'buver{}=buver.buver:buver_entry'.format(version_info.major)
                           ],
      },
      zip_safe=False)
