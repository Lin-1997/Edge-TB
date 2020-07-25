FROM python:3.6.8
WORKDIR /home/etree
COPY ./requirements.txt /home/etree
RUN pip install --upgrade pip -i http://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com
RUN pip install -r requirements.txt -i http://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com
CMD ["/bin/bash"]
