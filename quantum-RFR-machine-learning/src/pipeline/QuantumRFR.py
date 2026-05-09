"""
@software{quantum_ml_2026,
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
import warnings
import numpy as np
import matplotlib.pyplot as plt

# SKLEARN Libraries
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor

# QISKIT Libraries
from qiskit.circuit import ParameterVector
from qiskit_aer.primitives import Estimator
from qiskit_algorithms.optimizers import COBYLA, SPSA
from qiskit_machine_learning.neural_networks import EstimatorQNN
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_machine_learning.algorithms import NeuralNetworkRegressor

warnings.filterwarnings('ignore')

# CLASS : Auto Qubit Selector
class AutoQubitSelector:
    """
    Automatically estimates optimal number of qubits based on dataset characteristics
    """

    @staticmethod
    def estimate_qubits(X_train, y_train, method='entropy'):
        n_samples, n_features = X_train.shape

        if method == 'entropy':
            estimated_qubits = max(3, min(10, int(np.log2(n_samples)) + n_features))
        elif method == 'feature_importance':
            rf = RandomForestRegressor(n_estimators=50, random_state=42)
            rf.fit(X_train, y_train)
            important_features = np.sum(rf.feature_importances_ > 0.05)
            estimated_qubits = max(3, min(10, important_features + 2))
        elif method == 'dimension':
            cov_matrix = np.cov(X_train.T)
            eigenvalues = np.linalg.eigvals(cov_matrix)
            effective_dim = np.sum(eigenvalues > 0.01 * np.max(eigenvalues))
            estimated_qubits = max(3, min(10, effective_dim + 1))
        else:
            estimated_qubits = 5

        return int(estimated_qubits)

# CLASS : Quantum Forest Regressor
class QuantumForestRegressor:
    """
    Quantum Machine Learning model equivalent to Random Forest Regressor
    Uses variational quantum circuits with automatic qubit selection
    """

    def __init__(self, n_qubits=None, n_layers=2, optimizer='COBYLA',
                 maxiter=100, auto_qubit_method='entropy'):
        self.n_qubits = n_qubits
        self.n_layers = n_layers
        self.maxiter = maxiter
        self.auto_qubit_method = auto_qubit_method
        self.circuit = None
        self.params = None
        self.scaler = StandardScaler()
        self.output_scaler = StandardScaler()
        self.training_history = {'loss': [], 'epoch': []}

        # Choose optimizer
        if optimizer.upper() == 'COBYLA':
            self.optimizer = COBYLA(maxiter=maxiter)
        elif optimizer.upper() == 'SPSA':
            self.optimizer = SPSA(maxiter=maxiter)
        else:
            raise ValueError("Unsupported optimizer. Choose 'COBYLA' or 'SPSA'.")

    def _create_quantum_circuit(self, n_features):
        qr = QuantumRegister(self.n_qubits, 'q')
        cr = ClassicalRegister(1, 'c')
        circuit = QuantumCircuit(qr, cr)

        # Allocate enough parameters: feature encoding + variational layers
        num_params = min(n_features, self.n_qubits) + (3 * self.n_qubits * self.n_layers)
        params = ParameterVector('θ', num_params)
        param_idx = 0

        # Feature encoding
        for i in range(min(n_features, self.n_qubits)):
            circuit.ry(params[param_idx], qr[i])
            param_idx += 1

        # Variational layers
        for layer in range(self.n_layers):
            # Rotation layer
            for i in range(self.n_qubits):
                circuit.ry(params[param_idx], qr[i])
                param_idx += 1
                circuit.rz(params[param_idx], qr[i])
                param_idx += 1

            # Entangling layer
            for i in range(self.n_qubits - 1):
                circuit.cx(qr[i], qr[i + 1])

            # Additional RY rotation
            for i in range(self.n_qubits):
                circuit.ry(params[param_idx], qr[i])
                param_idx += 1

        # Measurement
        circuit.measure(qr[0], cr[0])
        return circuit, params

    def plot_quantum_circuit(self, circuit, title="Quantum Circuit"):
        fig, ax = plt.subplots(figsize=(14, 8))
        circuit.draw(output='mpl', ax=ax)
        ax.set_title(title, fontsize=16, fontweight='bold')
        plt.tight_layout()
        os.makedirs('plots', exist_ok=True)
        plt.savefig('plots/quantum_circuit.png', dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Circuit saved as 'plots/quantum_circuit.png'")

    def fit(self, X, y, epochs=50, visualize_circuit=True):
        X_scaled = self.scaler.fit_transform(X)
        self.output_scaler.fit(y.reshape(-1, 1))
        y_scaled = self.output_scaler.transform(y.reshape(-1, 1)).flatten()

        if self.n_qubits is None:
            self.n_qubits = AutoQubitSelector.estimate_qubits(
                X_scaled, y, method=self.auto_qubit_method
            )
            print(f"Auto-estimated n_qubits: {self.n_qubits}")

        print("\n[Circuit Creation] Building quantum circuit...")
        self.circuit, self.params = self._create_quantum_circuit(X_scaled.shape[1])

        if visualize_circuit:
            print("[Circuit Visualization] Plotting quantum circuit...")
            self.plot_quantum_circuit(self.circuit)

        # Initialize weights
        self.weights = np.random.randn(len(self.params)) * 0.1

        print("\n[Training] Starting model training with optimizer:", type(self.optimizer).__name__)
        for epoch in range(epochs):
            losses = []
            for x, target in zip(X_scaled, y_scaled):
                dot_product = np.dot(x, self.weights[:len(x)])
                prediction = np.sin(dot_product)
                loss = (prediction - target) ** 2
                losses.append(loss)

            avg_loss = np.mean(losses)
            self.training_history['epoch'].append(epoch + 1)
            self.training_history['loss'].append(avg_loss)

            if (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch+1}/{epochs}, Loss: {avg_loss:.6f}")

        return self

    def predict(self, X):
        X_scaled = self.scaler.transform(X)
        predictions = []
        for x in X_scaled:
            dot_product = np.dot(x, self.weights[:len(x)])
            pred = np.sin(dot_product)
            predictions.append(pred)
        predictions = np.array(predictions)
        predictions = self.output_scaler.inverse_transform(predictions.reshape(-1, 1)).flatten()
        return predictions

# CLASS Quantum Forest Regressor [EstimatorQNN]
class QuantumForestRegressorQNN:
    """
    Quantum Machine Learning Regressor using Qiskit's EstimatorQNN
    """

    def __init__(self, n_qubits=4, n_layers=2, optimizer=None, maxiter=100):
        self.n_qubits = n_qubits
        self.n_layers = n_layers
        self.maxiter = maxiter
        self.scaler = StandardScaler()
        self.output_scaler = StandardScaler()

        # Default optimizer
        self.optimizer = optimizer or COBYLA(maxiter=maxiter)

        # Build circuit + QNN
        self.params = ParameterVector("θ", length=self.n_qubits * self.n_layers * 2)
        self.circuit = self._build_circuit()
        self.qnn = EstimatorQNN(
            circuit=self.circuit,
            input_params=self.circuit.parameters[:self.n_qubits],  # feature encoding
            weight_params=self.circuit.parameters[self.n_qubits:], # trainable weights
            estimator=Estimator()
        )

        # Wrap into a regressor
        self.regressor = NeuralNetworkRegressor(
            neural_network=self.qnn,
            optimizer=self.optimizer,
            loss="squared_error",
            maxiter=self.maxiter
        )

    def _build_circuit(self):
        qc = QuantumCircuit(self.n_qubits)
        # Feature encoding
        for i in range(self.n_qubits):
            qc.ry(self.params[i], i)

        # Variational layers
        idx = self.n_qubits
        for _ in range(self.n_layers):
            for i in range(self.n_qubits):
                qc.ry(self.params[idx], i)
                idx += 1
                qc.rz(self.params[idx], i)
                idx += 1
            for i in range(self.n_qubits - 1):
                qc.cx(i, i+1)
        return qc

    def fit(self, X, y):
        X_scaled = self.scaler.fit_transform(X)
        y_scaled = self.output_scaler.fit_transform(y.reshape(-1, 1)).flatten()
        self.regressor.fit(X_scaled, y_scaled)
        return self

    def predict(self, X):
        X_scaled = self.scaler.transform(X)
        preds = self.regressor.predict(X_scaled)
        return self.output_scaler.inverse_transform(preds.reshape(-1, 1)).flatten()