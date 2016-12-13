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
    version = "0.7.0",
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
        "pycparser>=2.17",
        "pycparserext>=2016.2",
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
