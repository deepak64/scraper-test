# Automatically created by: scrapy deploy

from setuptools import setup, find_packages

setup(
    name         = 'project',
    version      = '1.0',
    packages     = find_packages(),
    entry_points = {'scrapy': ['settings = brightcorp.settings']},
    scripts      = ['bin/scheduler.py'],
    package_data={ 'brightcorp': ['resources/scraper_ftp.rsa'] }

)
