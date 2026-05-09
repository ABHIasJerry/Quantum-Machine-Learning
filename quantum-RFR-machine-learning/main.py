"""
@software{main_2026,
  author = {ABHIasJerry},
  title = {Quantum Machine Learning},
  year = {2026},
  version = 1.0.3
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
import argparse
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

def train_model():
    """
    Main execution function demonstrating quantum model with California Housing dataset
    """
    model_dir = 'logs'
    os.makedirs(model_dir, exist_ok=True)
    sys.stdout = open("logs/console-logs.txt", "w", encoding="utf-8")

    print("=" * 80)
    print("QUANTUM MACHINE LEARNING: Random Forest Regressor Equivalent")
    print("Dataset: Custom | OWNER: ABHIasJerry | Framework: Qiskit[2.4.1] | Python: 3.14")
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
    #### USE ANY ONE AT A TIME ###         ### THANK YOU.HAVE A NICE DAY ###
    ############################## DATASET #################################
    print("\n[1] Loading Target Dataset...")
    analyzer = DatasetAnalyzer("docs/")
    # data = analyzer._get_dataset()
    data = analyzer._filterout_stringtypes_from_df()
    data = data.fillna(data.mean(numeric_only=True))
    feature_names = analyzer._get_feature_names()
    print("Features: ", feature_names)
    print("DF shape: ", analyzer._get_shape())
    last_col = data.columns[-1]  # get the name of the last column name as target for predictions
    target_column = str(last_col)  # Example:  target_column = "SalePrice"

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
        optimizer='COBYLA',
        maxiter=50,
        auto_qubit_method='feature_importance'
    )  # optimizer = COBYLA / SPSA / QNG | auto_qubit_method = feature_importance / dimension / entropy

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

    comparison_df = {
                    'Metric': ['MSE', 'MAE', 'R² Score'],
                    'Random Forest': [f'{rf_mse:.6f}', f'{rf_mae:.6f}', f'{rf_r2:.6f}'],
                    'Quantum Model': [f'{q_mse:.6f}', f'{q_mae:.6f}', f'{q_r2:.6f}']
                    }

    try:
        model_dir = 'metrics'
        os.makedirs(model_dir, exist_ok=True)
        with open("metrics/metrics.json", "w") as json_file:
            json.dump(comparison_df, json_file, indent=4)
        print("Model metrics saved in metrics.json")
    except IOError as e:
        print(f"Error writing metrics to file: {e}")

    comparison_df = pd.DataFrame(comparison_df)
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
    print("\n[8] Feature Importance Analysis...")
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

    print("\n[9] Model Metadata...")
    metadata = {
        'model_name': 'Quantum Random Forest Regressor Eqv. v1.0.3',
        'dataset': f'{analyzer._get_training_dataset_name()}',
        'dataset_samples': len(X),
        'training_samples': len(X_train),
        'test_samples': len(X_test),
        'n_features': X.shape[1],
        'n_qubits': q_model.n_qubits,
        'n_layers': q_model.n_layers,
        'epochs_trained': q_model.maxiter,
        'final_loss': q_model.training_history['loss'][-1],
        'Q-test_mse': float(q_mse),
        'Q-test_mae': float(q_mae),
        'Q-test_r2': float(q_r2),
        'auto_qubit_method': q_model.auto_qubit_method,
        'description': 'Quantum Random Forest Regressor ML Eqv model training using IBM Qiskit'
    }

    for key, value in metadata.items():
        print(f"{key}: {value}")

    # Plot predictions comparison
    print("\n[10] Saving the model metadata...")
    try:
        model_dir = 'metadata'
        os.makedirs(model_dir, exist_ok=True)
        with open("metadata/metadata.txt", "w", encoding="utf-8") as file:
            json.dump(metadata, file, indent=4)  # indent for readability
        print("Metadata successfully saved to metadata.txt")
    except IOError as e:
        print(f"Error writing to file: {e}")

    print("\n" + "=" * 80)
    print("Quantum ML model & Classical ML model trainings completed successfully!")
    print("=" * 80)

    return q_model, rf_model, metadata

def test_model():
    """ To test the model predictions with custom data"""
    from src.test import test
    with open("src/test/test.json") as f:
        config = json.load(f)
    values = config["parameters"]["values"]
    print("Values got from test.json : -> ", values)
    test.test_predictions_with_custom_values(values)

def main():
    """ Main function """
    parser = argparse.ArgumentParser(description="Select a function to run")
    parser.add_argument(
        "function",
        choices=["train", "test"],
        help="Choose which function to run"
    )
    args = parser.parse_args()
    if args.function == "train":   # Train the model first
        q_model, rf_model, metadata = train_model()
    elif args.function == "test":  # Test the model after training
        test_model()

# Entry-point
if __name__ == "__main__":
    main()
################################################################
"""       
Command line arguments : python main.py train
                         python main.py test
"""
################################################################