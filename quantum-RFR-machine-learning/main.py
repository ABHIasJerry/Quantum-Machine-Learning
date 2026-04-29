"""
@software{main_2026,
  author = {ABHIasJerry},
  title = {Quantum Machine Learning},
  year = {2026},
  url = {https://github.com/ABHIasJerry/Quantum-Machine-Learning}
}
Quantum Machine Learning Model - Equivalent to Random Forest Regressor
Uses Qiskit framework with custom user dataset
Features automatic qubit selection based on dataset characteristics
"""
import os
import sys
import json
import pickle
import warnings
import pandas as pd
import matplotlib.pyplot as plt

# SKLEARN Libraries
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error

# Custom Libraries
from src.lib.DatasetManager import DatasetAnalyzer
from src.pipeline.QuantumRFR import QuantumForestRegressor

# Dataset [Optional]
from sklearn.datasets import fetch_california_housing

warnings.filterwarnings("ignore")

def main():
    """
    Main execution function demonstrating quantum model with California Housing dataset
    """
    model_dir = 'logs'
    os.makedirs(model_dir, exist_ok=True)
    sys.stdout = open("logs/console-logs.txt", "w", encoding="utf-8")

    print("=" * 80)
    print("QUANTUM MACHINE LEARNING: Forest Regressor Equivalent")
    print("Dataset: User Defined | Framework: Qiskit")
    print("=" * 80)

    ######################### SKLEARN DATASET ############################
    # # Load California Housing dataset
    # print("\n[1] Loading California Housing Dataset...")
    # housing = fetch_california_housing()
    # X, y = housing.data, housing.target
    # feature_names = housing.feature_names
    #
    # print(f"Dataset shape: {X.shape}")
    # print(f"Dataset shape: {y.shape}")
    # print(f"Features: {', '.join(feature_names)}")
    # print(f"Target range: [{y.min():.2f}, {y.max():.2f}]")
    ########################################################################

    ############################## DATASET ################################
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
    print("Features: ", feature_names)
    print("DF shape: ", analyzer._get_shape())

    data = pd.read_csv(selected_file)
    target_column = "target"  # edit the target column

    # data = data[target_column].astype("float64")   # convert the datatypes to same

    X = data.drop(columns=[target_column]).to_numpy()
    y = data[target_column].to_numpy()

    print(f"Dataset shape: {X.shape}")
    print(f"Target shape: {y.shape}")
    print(f"Features: {feature_names}")
    ########################################################################

    # Train-test split
    print("\n[2] Splitting Data (80-20)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"Training samples: {len(X_train)}")
    print(f"Test samples: {len(X_test)}")
    print("Training features shape:", X_train.shape)
    print("Testing features shape:", X_test.shape)
    print("Training target shape:", y_train.shape)
    print("Testing target shape:", y_test.shape)

    # Train classical Random Forest for comparison
    print("\n[3] Training Classical Random Forest Regressor...")
    rf_model = RandomForestRegressor(
        n_estimators=100,
        max_depth=20,
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)
    rf_pred = rf_model.predict(X_test)
    rf_mse = mean_squared_error(y_test, rf_pred)
    rf_mae = mean_absolute_error(y_test, rf_pred)
    rf_r2 = r2_score(y_test, rf_pred)

    model_dir = 'predictions'
    os.makedirs(model_dir, exist_ok=True)
    CLresult_df = pd.concat([pd.DataFrame(X_test), pd.DataFrame(rf_pred)], axis=1)
    CLresult_df.columns = feature_names
    CLresult_df.to_csv("predictions/classical-model-predictions.csv", index=False)
    print(f"Random Forest - MSE: {rf_mse:.6f}, MAE: {rf_mae:.6f}, R²: {rf_r2:.6f}")

    # Train Quantum Forest Regressor
    print("\n[4] Training Quantum Forest Regressor...")
    print("    Auto-estimating optimal number of qubits...")

    q_model = QuantumForestRegressor(
        n_layers=5,
        learning_rate=0.01,
        maxiter=50,
        auto_qubit_method='entropy'
    )

    # fit() now includes circuit visualization
    q_model.fit(X_train, y_train, visualize_circuit=True)
    q_pred = q_model.predict(X_test)
    q_mse = mean_squared_error(y_test, q_pred)
    q_mae = mean_absolute_error(y_test, q_pred)
    q_r2 = r2_score(y_test, q_pred)

    model_dir = 'predictions'
    os.makedirs(model_dir, exist_ok=True)
    QLresult_df = pd.concat([pd.DataFrame(X_test), pd.DataFrame(q_pred)], axis=1)
    QLresult_df.columns = feature_names
    QLresult_df.to_csv("predictions/quantum-model-predictions.csv", index=False)
    print(f"Quantum Model - MSE: {q_mse:.6f}, MAE: {q_mae:.6f}, R²: {q_r2:.6f}")

    # Results comparison
    print("\n" + "=" * 80)
    print("PERFORMANCE COMPARISON")
    print("=" * 80)

    comparison_df = pd.DataFrame({
        'Metric': ['MSE', 'MAE', 'R² Score'],
        'Random Forest': [f'{rf_mse:.6f}', f'{rf_mae:.6f}', f'{rf_r2:.6f}'],
        'Quantum Model': [f'{q_mse:.6f}', f'{q_mae:.6f}', f'{q_r2:.6f}']
    })

    print(comparison_df.to_string(index=False))
    print("=" * 80)

    # Save Classical & Quantum Forest Regressor
    print("\n[5] Saving Classical & Quantum Forest Regressor models...")
    model_dir = 'model'
    os.makedirs(model_dir, exist_ok=True)
    filepath = "model/quantum-model.pkl"
    with open(filepath, 'wb') as f:
        pickle.dump(q_model, f)
    filepath = "model/classical-model.pkl"
    with open(filepath, 'wb') as f:
        pickle.dump(rf_model, f)
    print("Classical & Quantum RF models saved...")

    # Plot training history
    print("\n[6] Plotting Training History...")
    plt.figure(figsize=(10, 5))
    plt.plot(q_model.training_history['epoch'], q_model.training_history['loss'],
             marker='o', linestyle='-', linewidth=2, markersize=4)
    plt.xlabel('Epoch', fontsize=12)
    plt.ylabel('Loss (MSE)', fontsize=12)
    plt.title('Quantum Model Training History', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    # Create the model directory if it doesn't exist
    model_dir = 'plots'
    os.makedirs(model_dir, exist_ok=True)
    plt.savefig('plots/quantum_training_history.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Training history saved to 'plots/quantum_training_history.png'")

    # Plot predictions comparison
    print("\n[7] Plotting Predictions Comparison...")
    plt.figure(figsize=(12, 5))

    plt.subplot(1, 2, 1)
    plt.scatter(y_test, rf_pred, alpha=0.5, s=20)
    plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()],
             'r--', lw=2, label='Perfect Prediction')
    plt.xlabel('True Values', fontsize=11)
    plt.ylabel('Predicted Values', fontsize=11)
    plt.title('Random Forest Predictions', fontsize=12, fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.subplot(1, 2, 2)
    plt.scatter(y_test, q_pred, alpha=0.5, s=20, color='green')
    plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()],
             'r--', lw=2, label='Perfect Prediction')
    plt.xlabel('True Values', fontsize=11)
    plt.ylabel('Predicted Values', fontsize=11)
    plt.title('Quantum Model Predictions', fontsize=12, fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    model_dir = 'plots'
    os.makedirs(model_dir, exist_ok=True)
    plt.savefig('plots/predictions_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Predictions comparison saved to 'plots/predictions_comparison.png'")

    # Feature importance (from RF model)
    print("\n[7.1] Feature Importance Analysis...")
    feature_names_copy = feature_names.copy()
    feature_names_copy.remove(target_column)
    importance_df = pd.DataFrame({
        'Feature': feature_names_copy,
        'Importance': rf_model.feature_importances_
    }).sort_values('Importance', ascending=False)

    print(importance_df.to_string(index=False))
    # Plot feature importance
    plt.figure(figsize=(8, 5))
    plt.barh(importance_df['Feature'], importance_df['Importance'])
    plt.xlabel("Importance")
    plt.ylabel("Feature")
    plt.title("Model Feature Importances")
    plt.gca().invert_yaxis()  # highest importance at top
    # plt.show()
    model_dir = 'plots'
    os.makedirs(model_dir, exist_ok=True)
    plt.savefig('plots/feature-importances.png', dpi=150, bbox_inches='tight')
    plt.close()

    print("\n[8] Model Metadata...")
    metadata = {
        'model_name': 'Quantum Forest Regressor v1.0',
        'dataset': 'User Defined',
        'dataset_samples': len(X),
        'training_samples': len(X_train),
        'test_samples': len(X_test),
        'n_features': X.shape[1],
        'n_qubits': q_model.n_qubits,
        'n_layers': q_model.n_layers,
        'learning_rate': q_model.learning_rate,
        'epochs_trained': q_model.maxiter,
        'final_loss': q_model.training_history['loss'][-1],
        'test_mse': float(q_mse),
        'test_mae': float(q_mae),
        'test_r2': float(q_r2),
        'auto_qubit_method': q_model.auto_qubit_method,
        'description': 'Quantum ML model equivalent to Random Forest Regressor using Qiskit'
    }

    for key, value in metadata.items():
        print(f"{key}: {value}")

    # Plot predictions comparison
    print("\n[9] Saving the model metadata...")
    try:
        with open("metadata.txt", "w", encoding="utf-8") as file:
            json.dump(metadata, file, indent=4)  # indent for readability
        print("Metadata successfully saved to metadata.txt")
    except IOError as e:
        print(f"Error writing to file: {e}")

    print("\n" + "=" * 80)
    print("Quantum ML model training completed successfully!")
    print("=" * 80)

    return q_model, rf_model, metadata

# Entry-point
if __name__ == "__main__":
    q_model, rf_model, metadata = main()