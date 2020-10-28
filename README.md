### Installation
1. At least 2 computers, each with 2-cores and 2G memory, one acts as
Controller and others act as Workers.  
2. Linux required.  
3. python3, python3-pip, docker and kubernetes required.  
4. systemd-resolved required, some systems like CentOS7 may need to
install and start (enable) it manually.  
5. On Controller:  
    1. Copy ```net/controller``` into Controller.  
    2. Type ```kubeadm config images list```  in terminal to list the suitable versions,
    and modify ```controller/setup-k8s.sh```.  
    3. The docker image can be obtained through the official registry.  
    4. For Chinese users, it may be better to use ```registry.aliyuncs.com/google_containers``` 
    instead of the official one.  
    5. Run ```controller/setup-k8s.sh``` with bash.  
6. On Worker:  
    1. Copy ```net/worker``` into Worker.  
    2. Similar to Controller, run```worker/setup-k8s.sh``` with bash.  
7. On Raspberry Pi (if you have, Raspberry Pi OS recommended):  
    1. python3, python3-pip, iproute2 required.  
    2. Copy ```net/worker``` into Raspberry Pi.  
### Attention
##### Make sure all .sh files use LF ('\n') as line separator, otherwise they may not be executed in Linux.
### Usage
1. On Controller, modify ```localAPIEndpoint:advertiseAddress``` and
```kubernetesVersion```in ```controller/kubeadm-init.yml```.  
2. On Controller, run ```controller/run-k8s.sh``` with bash.  
3. On Worker, join the K8s network.  
4. On Worker, make sure there exists ```/etc/cni/net.d/*flannel.conf*```,
and has the same name and content as the one in Controller.
You may just copy the file from Controller.  
5. On Controller, write ```controller/ctl_run_app.py``` to define your nodes and network,
see ```controller/ctl_run_examples.py``` for more.  
6. On Worker, prepare docker image, code and whatever needed to run your apps.  
7. On Raspberry Pi, prepare code and whatever needed to run your apps,
and make sure it's running the ```worker/worker_tc_init.py```.  
8. On Controller, run ```controller/ctl_run_app.py``` with python3.  
### Example: Dml
1. Set the hostname of the Raspberry Pis to r1, r2, ...  
2. Same with above usage 1-4.  
3. On Controller, write a connection matrix named ```bw.txt```in
```controller/dml/tools```, or modify ```controller/dml/tools/graph_gen.py```
and run it with python3 to randomly generate one.  
4. On Controller, modify ```controller/ctl_run_dml.py``` , set bandwidth
according to the ```bw.txt```. Please note that in ```ctl_run_dml.py``` you can only
set an integer bandwidth, but the value in ```bw.txt``` can be decimal.
You can regard ```bw.txt``` as some unit (e.g., 1.953mbps),
and set it to the downgrade unit (2000kbps) in ```ctl_run_dml.py```.  
5. On Controller, modify ```controller/dml/tools//env_addr.txt```.
The order of ```server_ip``` should be the same as the order in the ```ctl_run_dml.py```,
see ```controller/dml/tools/README.md``` for more.  
6. Prepare datasets:  
    1. Divide your data and distribute it to the Workers and Raspberry Pis.  
    2. On Controller, modify ```controller/dml/tools/env_datasets.txt``` .  
    3. Type ```python3 controller/dml/tools/conf_env_gen.py -T 1``` in terminal
    to generate datasets-only-env files, see ```controller/dml/tools/README.md``` for more.  
    3. Manually distribute ```controller/dml/env_datasets/*.env``` to corresponding
    Workers and Raspberry Pis in folder ```worker/dml/env/```.  
7. On Raspberry Pi, run ```worker/run-dml.sh``` with bash.  
8. On Controller, run ```controller/ctl_run_dml.py``` with python3 and
keep this python program running on a terminal (called Ter). It will display massages later.  
9. On Controller, when Ter display ```performance collection completed```,
you can modify ```controller/dml/tools/env_tree.txt``` to define the dml network topology,
see ```controller/dml/tools/README.md``` for more.  
10. On Controller, type ```python3 controller/dml/tools/conf_env_gen.py -T 2``` in terminal
to generate full-env files.  
11. On Controller, type ```curl localhost:9000/conf``` in terminal to auto send the full-env files
to the corresponding Workers and Raspberry Pi, and training will auto start.  
12. On Controller, when Ter display ```log files parsing completed```,
you can check the log files in ```controller/dml/log/```.  
13. On Worker, you may need to clean the cni config and delete the ```cni0``` nic
if you finished one test and wan to add some new Workers to start the next test.
For example, you have used Worker1 to complete a test,
and Worker1 has ```cni0``` nic with ip address 10.244.1.0.
Now you want to add a new Worker2 to start the next test,
k8s may assign 10.244.1.0 to Worker2 and 10.244.2.0 to Worker1.
If you don't clean the old cni config and delete ```cni0``` nic in Worker1,
it cannot set the ip address of ```cni0``` nic to 10.244.2.0.  
#### Dataset and Network Model in Dml
1. Write ```worker/dml/nns/nn_xx.py```, just like ```worker/dml/nns/nn_minst.py```.
2. Prepare datasets and distribute it to the Workers and Raspberry Pis.
3. Modify ```worker/dml/EL.py``` and ```worker/dml/perf_eval.py``` to loads your ```nn_xx.py```.  
