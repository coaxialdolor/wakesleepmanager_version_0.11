from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="wakesleepmanager",
    version="0.1.0",
    author="Petter",
    description="A cross-platform tool to manage wake and sleep states of network devices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[
        'wakeonlan>=2.1.0',
        'paramiko>=3.3.1',
        'click>=8.1.7',
        'rich>=13.7.0',
        'python-dotenv>=1.0.0',
        'ping3>=4.0.4',
    ],
    entry_points={
        'console_scripts': [
            'wake=wakesleepmanager.cli:wake_cli',
            'sleep=wakesleepmanager.cli:sleep_cli',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
