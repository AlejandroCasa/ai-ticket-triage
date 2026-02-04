# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Define environment variable for Python to run in unbuffered mode
ENV PYTHONUNBUFFERED=1

# Run the application using the module method to avoid path issues
CMD ["python", "-m", "src.main"]