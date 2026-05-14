# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . .

# Install FastAPI, Uvicorn (with standard for WebSockets), and Pydantic
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" pydantic

# Make port 80 available to the world outside this container
# Azure Web Apps for Containers usually look for port 80 by default
EXPOSE 80

# Run the app using uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]