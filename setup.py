#
# (c) 2023 Giorgio Gonnella, University of Goettingen, Germany
#
from setuptools import setup, find_packages

def readme():
  with open('README.md') as f:
    return f.read()

import sys
if not sys.version_info[0] == 3:
  sys.exit("Sorry, only Python 3 is supported")

setup(name='egctools',
      version='0.1',
      description=\
        'Tools for working with the Expected Genome Contents format',
      long_description=readme(),
      long_description_content_type="text/markdown",
      url='https://github.com/ggonnella/egctools',
      keywords="bioinformatics sequence features genomics",
      author='Giorgio Gonnella',
      author_email='gonnella@zbh.uni-hamburg.de',
      license='ISC',
      # see https://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Software Development :: Libraries',
      ],
      packages=find_packages(),
      install_requires=['textformats', 'fardes', 'tabrec'],
      zip_safe=False,
      include_package_data=True,
      package_data={"": ["data/egc-spec/egc.tf.yaml",
                         "data/egc-spec/egc_tags.tf.yaml",
                         "data/egc-spec/egc_tags.yaml",
                         "data/egc-spec/external_resource.tf.yaml",
                         "data/egc-spec/organism_groups.tf/yaml",
                         "data/egc-spec/usage_context.tf.yaml",
                         "data/egc-spec/expectation_rules.tf.yaml",
                         "data/egc-spec/genome_contents.tf.yaml",
                         "data/egc-spec/textual_sources.tf.yaml"]},
    )
