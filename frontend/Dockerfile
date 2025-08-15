# Use an official lightweight Python image
FROM python:3.10-slim

# set a working directory
WORKDIR /app

# # install system deps (if any needed by your requirements)
# RUN apt-get update && \
#     apt-get install -y --no-install-recommends \
#       build-essential && \
#     rm -rf /var/lib/apt/lists/*

# copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy the rest of your app’s code
COPY . .

# expose Streamlit’s default port
EXPOSE 8501

# tell Streamlit to listen on all addresses (so Docker can bind it)
ENV STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

# run your app
CMD ["streamlit", "run", "app.py"]
