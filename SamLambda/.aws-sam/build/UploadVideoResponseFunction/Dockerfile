FROM public.ecr.aws/lambda/python:3.9

# Install FFmpeg
RUN yum update -y && \
    yum install -y wget xz && \
    wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
    tar -xf ffmpeg-release-amd64-static.tar.xz && \
    cp ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ && \
    chmod +x /usr/local/bin/ffmpeg && \
    rm -rf ffmpeg-*

# Copy requirements and install dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install -r requirements.txt

# Copy function code
COPY app.py ${LAMBDA_TASK_ROOT}

CMD ["app.lambda_handler"]