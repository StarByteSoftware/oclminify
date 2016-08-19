from setuptools import setup, find_packages
try:
    import pypandoc
    long_description = pypandoc.convert("README.md", "rst")
except:
    from io import open
    long_description = open("README.md").read()


setup(
    name = "oclminify",
    description = "Minify OpenCL source files.",
    long_description = long_description,
    license = "BSD",
    version = "0.6.0",
    author = "StarByte Software, Inc.",
    author_email = "jbendig@starbytesoftware.com",
    maintainer = "James Bendig",
    url = "https://github.com/StarByteSoftware/oclminify",
    platforms = "Cross Platform",
    classifiers = [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers ",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
    ],
    packages = find_packages(),
    install_requires = [
        "pycparser>=2.14",
        "pycparserext>=2016.1",
    ],
    dependency_links = [
        # The 2.14 is over a year old as of 2016-07-15 and doesn't support
        # pragmas correctly. This commit is much newer and is known to work.
        "git+https://github.com/eliben/pycparser.git@ffd8cb7dfc4b80c79a500e27736db8f7bfc1186e#egg=pycparser-2.14",
    ],
    extras_require = {
        "build": ["PyOpenCL>=2016.1",],
    },
    entry_points = {
        "console_scripts": [
            "oclminify = oclminify.__main__:main",
        ],
    },
    test_suite = "tests.test_minifier",
)
