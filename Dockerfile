FROM python:3.12-slim
 
ENV PYTHONUNBUFFERED=1
 
WORKDIR /app
 
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
 
COPY . .
 
# Folders the app writes to; mounted as volumes in the deploy step
RUN mkdir -p data uploads
 
EXPOSE 8080
 
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]