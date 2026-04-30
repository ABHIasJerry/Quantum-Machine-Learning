##### This is the test file to check predictions with custom data ##########
import os, pickle
import pandas as pd

current_dir = os.getcwd()
# parent_dir = os.path.dirname(os.path.dirname(current_dir))

qmodelname = "model/quantum-model.pkl"
cmodelname = "model/classical-model.pkl"
qm_file_path = os.path.join(current_dir, qmodelname)
cm_file_path = os.path.join(current_dir, cmodelname)

# 1. Load the trained models from the pickle file
with open(qm_file_path, "rb") as qm:
    Qmodel = pickle.load(qm)
with open(cm_file_path, "rb") as cm:
    Cmodel = pickle.load(cm)

def test_predictions_with_custom_values(values):
    # # 2. Create a custom DataFrame with test input
    df = pd.read_csv("predictions/quantum-model-predictions.csv")
    df = df.drop(df.columns[-1], axis=1)
    feature_names = df.columns.tolist()
    test_data = pd.DataFrame([values])

    # 3. Make predictions
    Q_predictions = Qmodel.predict(test_data)
    C_predictions = Cmodel.predict(test_data)

    # 4. Print results
    sample_frame = pd.DataFrame([feature_names, values])
    print("\n <!> Quantum Predictions:", Q_predictions[0])
    print(" <!> Classical Predictions:", C_predictions[0])
    return None
################################################################################################