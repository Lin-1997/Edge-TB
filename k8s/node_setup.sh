#!/bin/bash
k=v1.18.3
g=k8s.grc.io
a=registry.aliyuncs.com/google_containers

images=(kube-proxy:${k}
pause:3.2)

for i in ${images[@]} ; do
	docker pull ${a}/${i}
	docker tag ${a}/${i} ${g}/${i}
	docker rmi ${a}/${i}
done

docker images
