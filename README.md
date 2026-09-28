# KaleemGpt

KaleemGPT

KaleemGPT is an AI-powered chatbot application designed to provide an
interactive conversational experience.

How to Run KaleemGPT

1. Clone the repository

git clone https://github.com/KaleemZdk/KaleemGpt.git

2. Navigate to the project directory

cd KaleemGPT

3. Create a virtual environment (optional but recommended)

conda create -n kaleemgpt python=3.11 -y

4. Activate the virtual environment

conda activate kaleemgpt

5. Install the required dependencies

Make sure requirements.txt is present in the project directory:

pip install -r requirements.txt

6. Configure environment variables

Create a .env file in the project directory and add the required API
keys.

Example:

OPENAI_API_KEY=your_api_key_here

Do not upload your .env file or expose API keys on GitHub.

7. Run the application

If the application uses Streamlit:

streamlit run app.py

If your main Python file has a different name, replace app.py with the
correct filename.

8. Open the application

After starting the application, open the local URL shown in the
terminal, usually:

http://localhost:8501

