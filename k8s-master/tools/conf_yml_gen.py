import json
import os


def gen_yml ():
	container_start_number = 1
	for dep_index in range (_server_number):
		# dep-的信息
		str_dep = '---\n' \
		          + 'apiVersion: apps/v1\n' \
		          + 'kind: Deployment\n' \
		          + 'metadata:\n' \
		          + '  name: d-etree-' + str (dep_index + 1) + '\n' \
		          + 'spec:\n' \
		          + '  selector:\n' \
		          + '    matchLabels:\n' \
		          + '      label: l-p-etree-' + str (dep_index + 1) + '\n' \
		          + '  template:\n' \
		          + '    metadata:\n' \
		          + '      labels:\n' \
		          + '        label: l-p-etree-' + str (dep_index + 1) + '\n' \
		          + '    spec:\n' \
		          + '      nodeName: name of the ' + str (dep_index + 1) + '^th node\n' \
		          + '      hostname: p-etree-' + str (dep_index + 1) + '\n' \
		          + '      containers:\n'
		# dep中每个host container的信息
		container_number = _container_number [dep_index]
		for host_index in range (container_start_number, container_number + 1):
			str_dep = str_dep \
			          + '      - name: n' + str (host_index) + '\n' \
			          + '        image: etree-node:v1.0\n' \
			          + '        imagePullPolicy: Never\n' \
			          + '        ports:\n' \
			          + '        - containerPort: ' + str (8000 + host_index) + '\n' \
			          + '        command: ["bash", "run.sh"]\n' \
			          + '        env:\n' \
			          + '        - name: NAME\n' \
			          + '          value: "n' + str (host_index) + '"\n' \
			          + '        - name: PORT\n' \
			          + '          value: "' + str (8000 + host_index) + '"\n' \
			          + '        volumeMounts:\n' \
			          + '        - name: node\n' \
			          + '          mountPath: /home/node\n'
		# dep中volume的信息
		str_dep = str_dep \
		          + '      volumes:\n' \
		          + '      - name: node\n' \
		          + '        persistentVolumeClaim:\n' \
		          + '          claimName: pvc-node\n'
		# svc的信息
		str_dep = str_dep \
		          + '---\n' \
		          + 'apiVersion: v1\n' \
		          + 'kind: Service\n' \
		          + 'metadata:\n' \
		          + '  name: s-etree-' + str (dep_index + 1) + '\n' \
		          + 'spec:\n' \
		          + '  selector:\n' \
		          + '    label: l-p-etree-' + str (dep_index + 1) + '\n' \
		          + '  type: NodePort\n' \
		          + '  ports:\n'
		# svc中每个host port的信息
		for host_index in range (container_start_number, container_number + 1):
			str_dep = str_dep \
			          + '  - name: n' + str (host_index) + '\n' \
			          + '    port: ' + str (8000 + host_index) + '\n' \
			          + '    targetPort: ' + str (8000 + host_index) + '\n' \
			          + '    nodePort: ' + str (30000 + host_index) + '\n'
		# 写入一个yml文件
		file_path = os.path.abspath (os.path.join (dirname, '../', 'dep-' + str (dep_index + 1) + '.yml'))
		with open (file_path, 'w')as f:
			f.writelines (str_dep)
		# 下一个文件用
		container_start_number = container_number + 1

	file_path = os.path.abspath (os.path.join (dirname, '../dep.sh'))
	with open (file_path, 'w') as f:
		str_dep_sh = '#!/bin/bash\n'
		for i in range (_server_number):
			str_dep_sh = str_dep_sh + 'kubectl delete -f dep-' + str (i + 1) + '.yml\n'
		for i in range (_server_number):
			str_dep_sh = str_dep_sh + 'kubectl create -f dep-' + str (i + 1) + '.yml\n'
		f.writelines (str_dep_sh)


def read_json (filename):
	file_path = os.path.abspath (os.path.join (dirname, filename))
	with open (file_path, 'r') as f:
		return json.loads (f.read ().replace ('\n', '').replace ('\r', '').replace ('\'', '\"'))


dirname = os.path.dirname (__file__)
env_addr_json = read_json ('env_addr.txt')
_server_number = env_addr_json ['server_number']
_container_number = env_addr_json ['container_number']
gen_yml ()
