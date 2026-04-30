import pandas as pd
import pickle

# 1. Load the trained models from the pickle file
with open("model/quantum-model.pkl", "rb") as qm:
    Qmodel = pickle.load(qm)
with open("model/classical-model.pkl", "rb") as cm:
    Cmodel = pickle.load(cm)

# 2. Create a custom DataFrame with test input
df = pd.read_csv("predictions/quantum-model-predictions.csv")
df = df.drop(df.columns[-1], axis=1)
feature_names = df.columns.tolist()
values = [] # add custom values you want
test_data = pd.DataFrame([feature_names], columns=values)

# 3. Make predictions
Q_predictions = Qmodel.predict(test_data)
C_predictions = Cmodel.predict(test_data)

# 4. Print results
print("Input DataFrame:")
print(test_data.to_string())
print("\nQuantum Predictions:", Q_predictions)
print("\nClassical Predictions:", C_predictions)