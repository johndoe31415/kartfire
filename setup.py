import setuptools

with open("README.md") as f:
	long_description = f.read()

setuptools.setup(
	name = "kartfire",
	packages = setuptools.find_packages(),
	version = "0.0.4",
	license = "gpl-3.0",
	description = "Toolkit to perform known-answer testing in Docker-isolated environments",
	long_description = long_description,
	long_description_content_type = "text/markdown",
	author = "Johannes Bauer",
	author_email = "joe@johannes-bauer.com",
	url = "https://github.com/johndoe31415/kartfire",
	download_url = "https://github.com/johndoe31415/kartfire/archive/v0.0.4.tar.gz",
	keywords = [ "testcase", "runner", "docker" ],
	install_requires = [
	],
	entry_points = {
		"console_scripts": [
			"kartfire = kartfire.__main__:main"
		]
	},
	include_package_data = True,
	classifiers = [
		"Development Status :: 5 - Production/Stable",
		"Intended Audience :: Developers",
		"License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
		"Programming Language :: Python :: 3",
		"Programming Language :: Python :: 3 :: Only",
		"Programming Language :: Python :: 3.10",
	],
)
