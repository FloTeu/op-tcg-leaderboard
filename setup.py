# setup.py

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py
import subprocess

class CustomBuild(_build_py):
    def run(self):
        # Run the frontend build script
        subprocess.run(['poetry', 'run', 'build-frontend'], check=True)
        # Continue with the normal build process
        _build_py.run(self)

setup(
    cmdclass={
        'build_py': CustomBuild,
    },
)
