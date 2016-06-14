# -*- mode: ruby -*-
# vi: set ft=ruby :

$script = <<SCRIPT
echo "\n Adding forager-dev to hosts file\n"
echo "192.168.101.101 forager-dev" >> /etc/hosts

echo "\n Updating python-dev\n"
apt-get update
apt-get install python-dev --fix-missing

echo "\n Installing pip dependencies\n"
pip install scrapyd scrapylib httplib2 ngram pysftp markdown2 urllib3 ndg-httpsclient==0.3.2 pyasn1==0.1.6

echo "\n Restarting scrapy\n"
service scrapyd restart

echo "\n Deploying brightcorp project\n"
cd /bright/scraper/brightcorp/ && scrapy deploy

echo "\n Deploying logsprune project\n"
cd /bright/scraper/logsprune/ && scrapy deploy

echo "\n Deploying geocoder project\n"
cd /bright/scraper/geocoder/ && scrapy deploy

echo "\n Sending ping to forager-dev\n"
python /bright/scraper/vagrant/ping.py forager-dev feedwizard f33dw1z4rd

echo "\n Writing ping and logsprune log deleter cron"
cat > /tmp/deleter.cron <<EOL
* * * * * python /bright/scraper/vagrant/ping.py forager-dev feedwizard feedwizard
0 * * * * cd /var/log/scrapyd/logsprune/deleter && rm -rf *
EOL

crontab /tmp/deleter.cron

rm -rf /tmp/deleter.cron

echo "\n FINISHED provisioning\n"
date > /etc/vagrant_provisioned_at
SCRIPT

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"


Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.box = "gatherer-dev"
  config.vm.box_url = "https://s3.amazonaws.com/bright_chef/gatherer-dev.box"

  config.vm.provider :virtualbox do |vb|
    vb.customize [
      "modifyvm", :id,
      "--memory", "512",
      "--cpus", "2",
      "--ioapic", "on"
      ]
  end

  config.vm.synced_folder "./", "/bright/scraper"

  config.vm.provision :shell, :inline => "echo \"America/Los_Angeles\" | sudo tee /etc/timezone && dpkg-reconfigure --frontend noninteractive tzdata"

  config.vm.define "gatherer1" do |gatherer1|
    gatherer1.vm.hostname = "gatherer-1"
    gatherer1.vm.network :private_network, ip: "192.168.101.102"
    gatherer1.vm.network "forwarded_port", guest: 22, host: 2121, auto_correct: true
  end

  config.vm.define "gatherer2" do |gatherer2|
    gatherer2.vm.hostname = "gatherer-2"
    gatherer2.vm.network :private_network, ip: "192.168.101.103"
  end

  config.vm.define "gatherer3" do |gatherer3|
    gatherer3.vm.hostname = "gatherer-3"
    gatherer3.vm.network :private_network, ip: "192.168.101.104"
  end

  config.vm.define "gatherer4" do |gatherer4|
    gatherer4.vm.hostname = "gatherer-4"
    gatherer4.vm.network :private_network, ip: "192.168.101.105"
  end

  config.vm.provision "shell", inline: $script
end
