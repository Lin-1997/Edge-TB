FROM tensorflow/tensorflow:1.15.0-py3
WORKDIR /home/node
COPY requirements.txt /home/node
RUN pip3 install --upgrade pip -i http://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com
RUN pip3 install -r requirements.txt -i http://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com
CMD ["/bin/bash"]
