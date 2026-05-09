import os
import pickle
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel

# Initialize FastAPI app
app = FastAPI()   # http://127.0.0.1:8000/predict

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


############################################################################

# PAYLOAD

"""
INPUT
{
  "values": [5.1, 3.5, 1.4, 0.2]
}

OUTPUT
{
  "quantum_prediction": 5.1,
  "classical_prediction": 3.5,
"""