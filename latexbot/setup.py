from setuptools import setup

with open("requirements.txt", "r") as f:
    install_requires = [s for s in f.read().splitlines() if not s.startswith("--")]

setup(
    name="latexbot",
    version="0.10.0-dev",
    description="Ryver bot",
    packages=["latexbot"],
    install_requires=install_requires,
    python_requires=">=3.6"
)
