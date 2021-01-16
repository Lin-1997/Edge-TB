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
2. From now on, all operations are done in Controller.
3. Prepare neural network model, just like what ```controller/dml_app/nns/nn_cifar10.py``` does.
4. Prepare datasets and split it, just like what ```controller/dml_tool/cifar10_splitter.py``` does.
5. Prepare DML, just like what ```controller/dml_app/EL.py``` does.
6. Update ```controller/dml_app/Dockerfile``` and ```controller/dml_app/dml_req.txt``` to meet your DML.
7. Modify ```controller/ctl_run_example.py```  to define your nodes and network.
8. Run ```controller/ctl_run_example.py``` with python3 and keep it running on a terminal (called Ter).
9. Wait until Ter display ```tc finish```.
10. Modify ```controller/dml_tool/conf_datasets.txt``` to define the data used by each node,
    see ```controller/dml_tool/README.md``` for more.
11. Type ```python3 controller/dml_tool/conf_generator.py -t 1``` in terminal to generate datasets-only-conf files.
12. Type ```curl localhost:9000/conf``` in terminal to auto send those datasets-only-conf files to each node.
13. Wait until Ter display ```performance collection completed```.
14. Modify ```controller/dml_tool/conf_structure.txt``` to define the DML structure,
    see ```controller/dml_tool/README.md``` for more.
15. Type ```python3 controller/dml_tool/conf_generator.py -t 2``` in terminal to generate full-conf files.
16. Type ```curl localhost:9000/conf?start=1``` in terminal to auto send those full-conf files to each node, and start
    training.
17. Wait until Ter display ```log files parsing completed```.
