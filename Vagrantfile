# -*- mode: ruby -*-
# vi: set ft=ruby :
#
# Coyright (c) 2016  Red Hat, Inc.
# Author: Tomas Hozza <thozza@redhat.com>

Vagrant.configure(2) do |config|
  config.vm.box = "fedora/23-cloud-base"

  # config.vm.provider "virtualbox" do |vb|
  #   # Display the VirtualBox GUI when booting the machine
  #   vb.gui = true
  #
  #   # Customize the amount of memory on the VM:
  #   vb.memory = "1024"
  # end

  config.vm.provision "shell", inline: <<-SHELL
    sudo dnf -y copr enable pavlix/network-testing
    sudo dnf -y install network-testing
    # sudo dnf -y install network-testing-deps
  SHELL
end
