### Installation

1. At least 2 computers, one acts as Controller, and others act as Workers (as physical nodes, class: Device or as
   emulator, class:ContainerServer).
2. |Role|Requirement|
   |---|---|
   |Controller|python3, python3-pip, NFS-Server|
   |Worker (Device)|python3, python3-pip, NFS-Client, iproute (iproute2)|
   |Worker (ContainerServer)|python3, python3-pip, NFS-Client, iproute (iproute2), Docker|
3. Copy ```controller``` into Controller and install the python packages defined in ```controller/ctl_req.txt```.
4. Copy ```worker``` into Worker and install the python packages defined in ```worker/agent_req.txt```.

### Usage

1. The only things you need to do in Worker is to run ```worker/agent.py``` with python3, perhaps with root privileges.
   We need to mount NFS and install python packages via python3-pip, which require root privileges.
2. All the following operations should be completed in the Controller.
3. Prepare neural network model, just like what ```controller/dml_app/nns/nn_cifar10.py``` does.
4. Prepare datasets and split it, just like what ```controller/dml_tool/cifar10_splitter.py``` does.
5. Prepare DML, just like what ```controller/dml_app/etree_learning.py``` does.
6. Update ```controller/dml_app/Dockerfile``` and ```controller/dml_app/dml_req.txt``` to meet your DML.
7. Modify ```controller/ctl_run_example.py```  to define your nodes and network.
8. Run ```controller/ctl_run_example.py``` with python3 and keep it running on a terminal (called Term).
9. It takes a while to deploy the tc settings, so please set your DML to start running after receiving a certain
   message, such as receiving a ```GET``` request for ```/start```.
10. Wait until Term displays ```tc finish```, and then start your DML.

### Example: Etree Learning

1. Same with above 1-10.
2. Modify ```controller/dml_tool/conf_datasets.txt``` to define the data used by each node,
   see ```controller/dml_tool/README.md``` for more.
3. Type ```python3 controller/dml_tool/conf_generator.py -t 1``` in terminal to generate datasets-only-conf files.
4. Type ```curl localhost:9000/conf``` in a terminal to send those datasets-only-conf files to each node.
5. Wait until Ter display ```performance collection completed```.
6. Modify ```controller/dml_tool/conf_structure.txt``` to define the DML structure,
   see ```controller/dml_tool/README.md``` for more.
7. Type ```python3 controller/dml_tool/conf_generator.py -t 2``` in terminal to generate full-conf files.
8. Type ```curl localhost:9000/conf?start=1``` in a terminal to send those full-conf files to each node.
9. Wait until Term display ```log files parsing completed```.
