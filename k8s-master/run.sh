#!/bin/bash
sudo swapoff -a

sudo rm $HOME/.kube/config

sudo kubeadm init \
	--apiserver-advertise-address=ip.of.the.master \
	--image-repository k8s.grc.io \
	--kubernetes-version=v1.19.1 \
	--pod-network-cidr=10.244.0.0/16

mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

kubectl create -f kube-flannel.yml
kubectl create -f nfs.yml
