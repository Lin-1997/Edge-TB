#!/bin/bash
k=v1.19.3
g=k8s.gcr.io
a=registry.aliyuncs.com/google_containers
images=(kube-proxy:${k}
kube-scheduler:${k}
kube-controller-manager:${k}
kube-apiserver:${k}
pause:3.2
etcd:3.4.13-0
coredns:1.7.0)
for i in ${images[@]} ; do
	docker pull ${a}/${i}
	docker tag ${a}/${i} ${g}/${i}
	docker rmi ${a}/${i}
done
docker pull quay.io/coreos/flannel:v0.12.0-amd64
docker images
