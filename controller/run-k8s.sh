#!/bin/bash
sudo swapoff -a

sudo rm $HOME/.kube/config

sudo kubeadm init --config=kubeadm-init.yml

mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

kubectl create -f kube-flannel.yml
