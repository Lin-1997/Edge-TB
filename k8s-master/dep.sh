#!/bin/bash
kubectl delete -f dep-1.yml
kubectl create -f dep-1.yml
