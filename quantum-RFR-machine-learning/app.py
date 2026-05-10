"""
@software{main_2026,
  author = {ABHIasJerry},
  title = {Quantum Machine Learning},
  year = {2026},
  version = 1.0.0
  url = {https://github.com/ABHIasJerry/Quantum-Machine-Learning}
}
Predictions using API call
"""
import os
import pickle
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import HTMLResponse

# Initialize FastAPI app
app = FastAPI()

# Load models once at startup
current_dir = os.getcwd()
qmodelname = "model/quantum-model.pkl"
cmodelname = "model/classical-model.pkl"
qm_file_path = os.path.join(current_dir, qmodelname)
cm_file_path = os.path.join(current_dir, cmodelname)

with open(qm_file_path, "rb") as qm:
    Qmodel = pickle.load(qm)
with open(cm_file_path, "rb") as cm:
    Cmodel = pickle.load(cm)

# Define request schema
class InputValues(BaseModel):
    values: list  # expects a list of feature values in order

@app.get("/", response_class=HTMLResponse)
async def welcome():
    html_content = """
    <html>
        <head>
            <title>Quantum Prediction API - v1</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background-color: #f0f8ff;
                    text-align: center;
                    padding-top: 100px;
                }
                h1 {
                    color: #2e8b57;
                }
                p {
                    font-size: 18px;
                    color: #555;
                }
            </style>
        </head>
        <body>
            <h1>🌟 Welcome to Abhinaba's Quantum Prediction API! 🌟</h1>
            <h2>🔮 API Prediction Call 🔮</h2>
        
            <p>Send a POST request to the FastAPI endpoint:</p>
            <p><strong>Endpoint:</strong> http://127.0.0.1:8000/predict</p>
        
            <p><strong>JSON Payload Example:</strong></p>
            <pre>
        {
          "values": [12.47,18.6,81.09, .....]   // pass the value list
        }
            </pre>
        
            <p><strong>Response Example:</strong></p>
            <pre>
        {
          "quantum_prediction": 0.7258717182277986,
          "classical_prediction": 1.0
        }
            </pre>
        
            <p>This instruction should be followed while using the API call in POSTMAN / ...</p>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/predict")
def predict(input_data: InputValues):
    # Load feature names from your CSV (used to align input order)
    df = pd.read_csv("predictions/quantum-model-predictions.csv")
    df = df.drop(df.columns[-1], axis=1)
    feature_names = df.columns.tolist()

    # Convert input values into DataFrame
    test_data = pd.DataFrame([input_data.values], columns=feature_names)

    # Run predictions
    Q_predictions = Qmodel.predict(test_data)
    C_predictions = Cmodel.predict(test_data)

    # Return results as JSON
    return {
        "quantum_prediction": Q_predictions[0],
        "classical_prediction": C_predictions[0]
    }