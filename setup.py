from setuptools import find_packages, setup

setup(
    author="Zackary Troop",
    name="wave-plus-exporter",
    version="1.0.0",
    url="https://github.com/ztroop/wave-plus-exporter",
    license="MIT",
    description="Prometheus exporter for Airthings Wave Plus device with SMS alerting.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=["tests"]),
    install_requires=[
        "wave-reader>=0.0.10",
        "prometheus-client>=0.14.1",
        "bleak>=0.14.3",
        "boto3>=1.24.5",
    ],
    python_requires=">=3.7.*",
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)