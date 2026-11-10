# Throwaway sandbox for the free pre-screen (rig/e2e/prescreen.py): an Ubuntu user "user" (password "password",
# sudo) like the OSWorld VM, the tools the tasks use, no network at run time (docker run --network none).
FROM ubuntu:22.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      python3 git sudo cron rsync file zip unzip xz-utils ca-certificates && rm -rf /var/lib/apt/lists/* && \
    useradd -m -s /bin/bash user && echo 'user:password' | chpasswd && usermod -aG sudo user && \
    chmod u+s /usr/bin/crontab || true
USER user
WORKDIR /home/user
