# Use the official Python base image
FROM python:3.13-slim

# Set environment variables to prevent Python from writing .pyc files and unbuffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed for GeoDjango/psycopg2
RUN apt-get update && apt-get install -y \
    build-essential \
    binutils \
    gdal-bin \
    libgdal-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the Django project files
COPY . /app/