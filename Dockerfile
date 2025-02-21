FROM langchain/langgraph-api:3.13

# Set environment variable to disable output buffering
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# If you have additional Python dependencies beyond what's provided by the base image,
# copy your requirements.txt and install them.
# If the base image already has everything you need, you can omit this.
COPY requirements.txt .
RUN pip install --upgrade pip --no-cache-dir && \
    pip install --no-cache-dir -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org

# Copy the rest of your application code into the container
COPY . .

# Expose port 8000 for the FastAPI app
EXPOSE 8000

# Start the FastAPI application using Uvicorn
CMD ["uvicorn", "serve:app", "--host", "0.0.0.0", "--port", "8000"]