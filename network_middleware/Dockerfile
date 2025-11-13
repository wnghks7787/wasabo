FROM mitmproxy/mitmproxy:7.0.4

RUN sed -i 's/deb.debian.org/archive.debian.org/g' /etc/apt/sources.list
RUN sed -i 's|security.debian.org/debian-security|archive.debian.org/debian-security|g' /etc/apt/sources.list
RUN sed -i '/buster-updates/d' /etc/apt/sources.list

# Updating apt to see and install Google Chrome
RUN apt update && apt install -y python3-pip unzip gnupg wget curl git
RUN pip3 install --upgrade pip
RUN pip3 install requests selenium-wire beautifulsoup4 pyblake2
RUN pip3 install git+https://github.com/lukect/undetected-chromedriver.git selenium~=4.8.0

# Adding trusting keys to apt for repositories
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -

# Adding Google Chrome to the repositories
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'

RUN apt update && apt install -y google-chrome-stable 

# Download the Chrome Driver
RUN wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE`/chromedriver_linux64.zip

# Unzip the Chrome Driver into /usr/local/bin directory
RUN unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/

# Set display port as an environment variable
ENV DISPLAY=:99

# EXPOSE 8080:8080

# ENTRYPOINT ["mitmdump"]
