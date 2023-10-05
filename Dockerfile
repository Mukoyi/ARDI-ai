# Base image
FROM python:3.9

# Create app directory
WORKDIR /app

ADD https://www.google.com /time.now

# A wildcard is used to ensure both package.json AND package-lock.json are copied
COPY requirements.txt ./requirements.txt

# Install app dependencies
RUN pip install -r requirements.txt
# Bundle app source
COPY . .


EXPOSE 80
EXPOSE 443
# run app
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=80", "--server.address=0.0.0.0"]