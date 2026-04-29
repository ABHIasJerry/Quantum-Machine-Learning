
from src.lib.DatasetManager import DatasetAnalyzer
import pandas as pd
import pickle
import os

# 1. Load your dataset (replace with your actual file or DataFrame)
print("\n[1] Loading Target Dataset...")
files = os.listdir("docs")
csv_files = [f for f in files if f.endswith(".csv")]
if csv_files:
    selected_file = os.path.join("docs", csv_files[0])  # pick the first one
    print("Selected file:", selected_file)
else:
    print("No CSV files found in docs.")

analyzer = DatasetAnalyzer(selected_file)
feature_names = analyzer._get_feature_names()
df = pd.DataFrame({
    'feature_names': feature_names,
    'values': [4, 5, 6],
})

# 2. Load the trained model from a .pkl file
with open("model/quantum-model.pkl", "rb") as f:
    model = pickle.load(f)

# 3. Make predictions
predictions = model.predict(df)

# 4. Convert predictions to DataFrame
predicted_df = pd.DataFrame(predictions, columns=['Prediction'])

# # 5. Save predictions to CSV
# predicted_df.to_csv("predictions.csv", index=False)

print("Predictions: ", predicted_df['Prediction'])
