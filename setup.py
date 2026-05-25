from setuptools import find_packages, setup

setup(
    author="Zackary Troop",
    name="wave-plus-exporter",
    version="1.1.0",
    url="https://github.com/ztroop/wave-plus-exporter",
    license="MIT",
    description="Prometheus exporter for Airthings Wave Plus devices.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=["tests"]),
    install_requires=[
        "wave-reader>=2.0.0",
        "prometheus-client>=0.14.1",
        "loguru>=0.6.0",
    ],
    python_requires=">=3.10",
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.10",
    ],
)
