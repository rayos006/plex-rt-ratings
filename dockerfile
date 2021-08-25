FROM python:3.8

WORKDIR /app

COPY ./requirements.txt ./requirements.txt
COPY ./ratings.py ./ratings.py

# Install python modules
RUN pip install -r requirements.txt

# Run the script
CMD ["python", "ratings.py"]