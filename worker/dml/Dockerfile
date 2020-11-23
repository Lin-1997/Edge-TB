FROM tensorflow/tensorflow:2.2.1-py3
RUN apt update && apt install apt iproute2 net-tools iperf3 -y
COPY ../requirements.txt /home
WORKDIR /home
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt
# For Chinese users
# RUN pip3 install --upgrade pip -i http://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com
# RUN pip3 install -r requirements.txt -i http://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com
CMD ["/bin/bash"]
