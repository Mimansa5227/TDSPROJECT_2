import os
import sys
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import httpx
import openai
import requests
from io import StringIO
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest

# Ensure OpenAI API token is set
AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN")
if not AIPROXY_TOKEN:
    print("Error: AIPROXY_TOKEN environment variable not set.")
    sys.exit(1)

def load_dataset(file_path):
    try:
        # Attempt to read the file using UTF-8 encoding. If the file contains non-UTF-8 encoded characters, the program will try a fallback encoding.
        data = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")
        print(f"Data loaded successfully from {file_path}")  
        return data 
    except UnicodeDecodeError:
        # If there is a UnicodeDecodeError (i.e., UTF-8 decoding fails), attempt to read the file using Latin1 encoding.
        try:
            data = pd.read_csv(file_path, encoding="latin1", on_bad_lines="skip")
            print(f"Data loaded successfully from {file_path}") 
            return data 
        except Exception as e:
            # If any other error occurs during loading (e.g., file not found), print the error message.
            print(f"Error loading data: {e}")
            return None 
    except Exception as e:
        # Handle any other general exceptions (e.g., invalid file path).
        print(f"Error loading data: {e}")
        return None 

def analyze_data(df):
    """Perform generic analysis on the dataset."""
    analysis = {
        "shape": df.shape,
        "columns": df.dtypes.to_dict(),
        "missing_values": df.isnull().sum().to_dict(),
        "summary_stats": df.describe(include='all').to_dict(),
    }
    return analysis

def detect_outliers(df):
    """Detect outliers using Isolation Forest."""
    numeric_data = df.select_dtypes(include=[np.number]).dropna()
    df['Outlier'] = np.nan 
    if not numeric_data.empty:
        clf = IsolationForest(random_state=42)
        outliers = clf.fit_predict(numeric_data)
        df.loc[numeric_data.index, 'Outlier'] = outliers  # Only assign values where numeric_data exists
    return df

def cluster_data(df):
    """Perform KMeans clustering on numeric data."""
    numeric_data = df.select_dtypes(include=[np.number]).dropna()
    df['Cluster'] = np.nan
    if numeric_data.shape[0] >= 5 and numeric_data.shape[1] >= 2:
        kmeans = KMeans(n_clusters=3, random_state=42)
        cluster = kmeans.fit_predict(numeric_data)
        df.loc[numeric_data.index, 'Cluster'] = cluster  # Only assign values where numeric_data exists
    return df

def visualize_data(data, output_dir):
   # Generate visualizations from the analysis.
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Create a histogram for each numerical column
    for column in data.select_dtypes(include=["number"]).columns:
        plt.figure(figsize=(8, 6))
        sns.histplot(data[column], kde=True, bins=30)
        plt.title(f"Distribution of {column}")
        plt.xlabel(column)
        plt.ylabel("Frequency")
        plt.savefig(f"{output_dir}/{column}_histogram.png")
        plt.close()

def query_llm(prompt, functions=None):
    """Send a query to the LLM and return its response."""
    try:
        url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AIPROXY_TOKEN}"  # Authorization header with the AI Proxy token
        }

        # Prepare the payload with the model and the message prompt.
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}]
        }

        # Make the POST request to the AI Proxy API.
        response = requests.post(url, headers=headers, json=payload)
        response = response.json()
        return response['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error querying LLM: {e}")
        sys.exit(1)

def execute_llm_code(prompt):
    """Ask the LLM to generate Python code for advanced analysis and execute it."""
    try:
        response = query_llm(prompt)
        print("Generated Python Code:")
        print(response)
        exec(response, globals())
    except Exception as e:
        print("Error executing LLM-generated code")

def suggest_and_execute_analysis(df, filename):
    """Ask the LLM to suggest further analysis and execute the Python code it provides."""
    prompt = (
        "Based on the following dataset information, suggest Python code for further analysis"
        f"Get data from file {filename}"
        f":\n Write Python code only. Do not include any markdown formatting like ``` or any explanations—just the plain Python code output."
        f"Column types: {df.dtypes.to_dict()}\n"
        f"Summary stats: {df.describe(include='all').to_dict()}"
    )
    execute_llm_code(prompt)

def generate_readme(df, analysis, output_dir):
    """Generate the README.md file with the results."""
    print("Now, creating the Readme file , of the analysis and suggesting insights")
    prompt = (
        "Create a narrative of the analysis and suggest insights from the data. Mention any charts provided as well.\n"
        f"Data shape: {analysis['shape']}.\n"
        f"Column types: {analysis['columns']}.\n"
        f"Missing values: {analysis['missing_values']}.\n"
        f"Summary stats: {analysis['summary_stats']}.\n"
    )
    story = query_llm(prompt)

    with open(os.path.join(output_dir, "README.md"), "w") as readme_file:
        readme_file.write(story)

def main():
    # Prompt to get csv file from user
    if len(sys.argv) < 2:
        print("Usage: python autolysis.py <dataset.csv>")
        sys.exit(1)  # Exit if the csv file is not provided in argument
    
    file_path = sys.argv[1] 
    dir = os.path.splitext(os.path.basename(file_path))[0]
    df = load_dataset(file_path)
    analysis = analyze_data(df)
    df = detect_outliers(df)
    df = cluster_data(df)
    charts = visualize_data(df, dir  )
    suggest_and_execute_analysis(df, file_path)
    generate_readme(df, analysis, dir )

if __name__ == "__main__":
    main()