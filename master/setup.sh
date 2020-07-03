#!/bin/bash
set -e

k=v1.18.3
g=k8s.grc.io
a=registry.aliyuncs.com/google_containers

images=(kube-proxy:${k}
kube-scheduler:${k}
kube-controller-manager:${k}
kube-apiserver:${k}
pause:3.2
etcd:3.4.3-0
coredns:1.6.7)

for i in ${images[@]} ; do
	docker pull ${a}/${i}
	docker tag ${a}/${i} ${g}/${i}
	docker rmi ${a}/${i}
done

docker images
