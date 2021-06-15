
FROM python:3.9-slim
LABEL maintainer=shaanan@cohney.info

# install dependencies for the cs50 tools check50 and style50
RUN echo 'deb http://deb.debian.org/debian buster-backports main' >  /etc/apt/sources.list.d/backports.list
RUN apt-get update && apt-get upgrade -y && apt-get install -y\
	bash \
	clang-11/buster-backports \
	astyle \
	&& apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install  --no-cache-dir check50 style50 rich
RUN ln -s /usr/bin/clang-11 /usr/bin/clang

# RUN apk --update add clang
# RUN apk --update add bash
# RUN apk --update add musl-dev
# RUN apk --update add build-base

# create a user so we are not root
RUN adduser cs50 -u 1001  \
	&& mkdir -p /src \
	&& chown -R cs50: /src

COPY docker-entrypoint /
RUN chmod +x /docker-entrypoint
ENTRYPOINT [ "/docker-entrypoint" ]

USER cs50
WORKDIR /src

# /src is the source code volume mountpoint
VOLUME /src
