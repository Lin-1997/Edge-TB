FROM tensorflow/tensorflow:1.15.0-py3
WORKDIR /home/etree
COPY ./requirements.txt /home/etree
RUN pip install --upgrade pip -i http://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com
RUN pip install -r requirements.txt -i http://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com
CMD ["/bin/bash"]
