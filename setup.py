from setuptools import setup, find_packages

setup(
    name="ai_review",
    version="0.1",
    packages=find_packages(),
    install_requires=[],
    entry_points={
        "console_scripts": [
            "ai-review=ai_review.cli:main",
        ],
    },
)
