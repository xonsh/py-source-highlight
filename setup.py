#!/usr/bin/env python3
import os
from distutils.core import setup
from distutils.extension import Extension

from Cython.Build import cythonize


extensions = [
    Extension("srchilite.bindings", ["srchilite/bindings.pyx"], libraries=["source-highlight"])
]


def main(args=None):
    with open(os.path.join(os.path.dirname(__file__), "README.md"), "r") as f:
        readme = f.read()

    setup(
        name="py-source-highlight",
        version="0.0.0",
        description="Python Bindings & Pygments-like Interface to source-highlight",
        long_description=readme,
        license="BSD",
        author="Anthony Scopatz",
        maintainer="Xonsh Core Developers",
        author_email="xonsh@googlegroups.org",
        url="https://github.com/xonsh/py-source-highlight",
        platforms="Cross Platform",
        classifiers=["Programming Language :: Python :: 3"],
        ext_modules=cythonize(extensions, language_level=3),
        zip_safe=False,
        packages=["srchilite"],
        package_dir={"srchilite": "srchilite"},
        package_data={"srchilite": ["*.pxd", "*.so", "*.dylib"]},
    )


if __name__ == "__main__":
    main()
