#!/bin/bash
sudo apt-get install python-dev libffi-dev libssl-dev libxml2-dev libxslt1-dev libxslt-dev python-dev lib32z1-dev
sudo pip install --upgrade pip
sudo apt-get purge python-openssl
sudo pip install pyopenssl
sudo pip install --upgrade scrapy
sudo pip install hdrhistogram
cd /bright/scraper/brightcorp/
# verify this works
#source ~/.bashrc
#scrapy crawl bluearrow -a extract=1 -a url="http://www.bluearrow.co.uk/pages/results.aspx"
sudo apt-get update
sudo apt-get install scrapyd --fix-missing
sudo service scrapyd restart
sudo pip install scrapyd-client
scrapyd-deploy
# verify this works
#curl -d "url= http://www.bluearrow.co.uk/pages/results.aspx&mining_job_id=999&iteration=1&management_node=127.0.0.1&username=feedwizard&password=f33dw1z4rd&protocol=http&robots_obey=1&extract=1&project=brightcorp&spider=bluearrow" 127.0.0.1:6800/schedule.json
