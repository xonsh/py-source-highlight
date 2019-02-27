import os
from distutils.core import setup
from distutils.extension import Extension

from Cython.Build import cythonize


extensions = [Extension("srchilite", ["srchilite/*.pyx"])]


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
        maintainer="Anthony Scopatz",
        author_email="scopatz@gmail.com",
        url="https://github.com/xonsh/xonsh",
        platforms="Cross Platform",
        classifiers=["Programming Language :: Python :: 3"],
        ext_modules=cythonize(extensions, language="c++"),
    )


if __name__ == "__main__":
    main()
