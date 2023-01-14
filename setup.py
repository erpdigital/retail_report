from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in retail_report/__init__.py
from retail_report import __version__ as version

setup(
	name="retail_report",
	version=version,
	description="Retail Report",
	author="Alimerdan Rahimov",
	author_email="Alimerdanrahimov@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
