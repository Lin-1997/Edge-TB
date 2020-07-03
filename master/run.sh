sudo swapoff -a

sudo rm $HOME/.kube/config

sudo kubeadm init \
	--apiserver-advertise-address=192.168.1.11 \
	--image-repository k8s.grc.io \
	--kubernetes-version=v1.18.3 \
	--pod-network-cidr=10.244.0.0/16

mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

kubectl apply -f kube-flannel.yml
