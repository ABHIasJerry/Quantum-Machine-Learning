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
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

warnings.filterwarnings('ignore')


class AutoQubitSelector:
    """
    Automatically estimates optimal number of qubits based on dataset characteristics
    """

    @staticmethod
    def estimate_qubits(X_train, y_train, method='entropy'):
        """
        Estimate optimal number of qubits using multiple heuristics

        Args:
            X_train: Training features
            y_train: Training labels
            method: 'entropy', 'feature_importance', or 'dimension'

        Returns:
            Estimated number of qubits
        """
        n_samples, n_features = X_train.shape

        if method == 'entropy':
            # Based on information entropy of dataset
            estimated_qubits = max(3, min(10, int(np.log2(n_samples)) + n_features))

        elif method == 'feature_importance':
            # Use random forest to estimate feature importance
            rf = RandomForestRegressor(n_estimators=50, random_state=42)
            rf.fit(X_train, y_train)
            important_features = np.sum(rf.feature_importances_ > 0.05)
            estimated_qubits = max(3, min(10, important_features + 2))

        elif method == 'dimension':
            # Based on effective dimensionality
            cov_matrix = np.cov(X_train.T)
            eigenvalues = np.linalg.eigvals(cov_matrix)
            effective_dim = np.sum(eigenvalues > 0.01 * np.max(eigenvalues))
            estimated_qubits = max(3, min(10, effective_dim + 1))

        else:
            estimated_qubits = 5

        return int(estimated_qubits)


class QuantumForestRegressor:
    """
    Quantum Machine Learning model equivalent to Random Forest Regressor
    Uses variational quantum circuits with automatic qubit selection
    """

    def __init__(self, n_qubits=None, n_layers=2, learning_rate=0.01,
                 maxiter=100, auto_qubit_method='entropy'):
        """
        Initialize Quantum Forest Regressor

        Args:
            n_qubits: Number of qubits (auto-estimated if None)
            n_layers: Number of circuit layers
            learning_rate: Optimizer learning rate
            maxiter: Maximum iterations for training
            auto_qubit_method: Method for qubit estimation
        """
        self.n_qubits = n_qubits
        self.n_layers = n_layers
        self.learning_rate = learning_rate
        self.maxiter = maxiter
        self.auto_qubit_method = auto_qubit_method
        self.qnn = None
        self.optimizer = None
        self.weights = None
        self.circuit = None
        self.params = None
        self.scaler = StandardScaler()
        self.output_scaler = StandardScaler()
        self.training_history = {'loss': [], 'epoch': []}

    def _create_quantum_circuit(self, n_features):
        """
        Create parameterized quantum circuit

        Args:
            n_features: Number of input features

        Returns:
            QuantumCircuit with parameters
        """
        qr = QuantumRegister(self.n_qubits, 'q')
        cr = ClassicalRegister(1, 'c')
        circuit = QuantumCircuit(qr, cr)

        # Parameter vector for variational circuit
        params = ParameterVector('θ', self.n_qubits * self.n_layers * 3)
        param_idx = 0

        # Feature encoding layer (angle encoding)
        for i in range(min(n_features, self.n_qubits)):
            circuit.ry(params[param_idx % len(params)], qr[i])
            param_idx += 1

        # Variational layers
        for layer in range(self.n_layers):
            # Rotation layer
            for i in range(self.n_qubits):
                circuit.ry(params[param_idx % len(params)], qr[i])
                param_idx += 1
                circuit.rz(params[param_idx % len(params)], qr[i])
                param_idx += 1

            # Entangling layer
            for i in range(self.n_qubits - 1):
                circuit.cx(qr[i], qr[i + 1])

            # Additional RY rotation
            for i in range(self.n_qubits):
                circuit.ry(params[param_idx % len(params)], qr[i])
                param_idx += 1

        # Measurement
        circuit.measure(qr[0], cr[0])

        return circuit, params

    def plot_quantum_circuit(self, circuit, title="Quantum Circuit"):
        """
        Plot the quantum circuit using matplotlib.

        Args:
            circuit: QuantumCircuit to plot
            title: Title for the plot
        """
        fig, ax = plt.subplots(figsize=(14, 8))

        # Draw the circuit
        circuit.draw(output='mpl', ax=ax)

        ax.set_title(title, fontsize=16, fontweight='bold')
        plt.tight_layout()
        # Create the plots directory if it doesn't exist
        plot_dir = 'plots'
        os.makedirs(plot_dir, exist_ok=True)
        plt.savefig('plots/quantum_circuit.png', dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Circuit saved as 'plots/quantum_circuit.png'")

    def fit(self, X, y, epochs=50, learning_rate=0.01, visualize_circuit=True):
        """
        Train the quantum model.

        Args:
            X: Training features
            y: Training labels
            epochs: Number of training epochs
            learning_rate: Learning rate for gradient descent
            visualize_circuit: Whether to visualize the quantum circuit
        """
        X_scaled = self.scaler.fit_transform(X)
        self.output_scaler.fit(y.reshape(-1, 1))
        y_scaled = self.output_scaler.transform(y.reshape(-1, 1)).flatten()

        # Auto-estimate number of qubits if not provided
        if self.n_qubits is None:
            self.n_qubits = AutoQubitSelector.estimate_qubits(
                X_scaled, y, method=self.auto_qubit_method
            )
            print(f"Auto-estimated n_qubits: {self.n_qubits}")

        # Create and visualize the quantum circuit
        print("\n[Circuit Creation] Building quantum circuit...")
        self.circuit, self.params = self._create_quantum_circuit(X_scaled.shape[1])

        if visualize_circuit:
            print("[Circuit Visualization] Plotting quantum circuit using matplotlib...")
            self.plot_quantum_circuit(self.circuit, title="Quantum Circuit Architecture")

        # Initialize weights with correct shape: (n_features,)
        self.weights = np.random.randn(X_scaled.shape[1]) * 0.1

        # Initialize training history with both 'epoch' and 'loss' keys
        self.training_history = {'epoch': [], 'loss': []}

        print("\n[Training] Starting model training...")
        for epoch in range(epochs):
            epoch_loss = 0

            for x, target in zip(X_scaled, y_scaled):
                # Forward pass
                dot_product = np.sum(x * self.weights)
                prediction = np.mean(np.sin(dot_product))

                # Backward pass - simple gradient descent
                loss = (prediction - target) ** 2
                epoch_loss += loss

                # Gradient computation
                grad = 2 * (prediction - target) * np.cos(dot_product) * x

                # Update weights
                self.weights -= learning_rate * grad

            avg_loss = epoch_loss / len(X_scaled)

            # Store both epoch and loss
            self.training_history['epoch'].append(epoch + 1)
            self.training_history['loss'].append(avg_loss)

            if (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch + 1}/{epochs}, Loss: {avg_loss:.6f}")

        return self

    def predict(self, X):
        """
        Make predictions on new data.

        Args:
            X: Input features (n_samples, n_features)

        Returns:
            Predictions (n_samples,)
        """
        X_scaled = self.scaler.transform(X)
        predictions = []

        for x in X_scaled:
            # Fix: Use only the first n_features weights
            # The weights should have shape (n_features,) not (n_features * n_layers,)
            dot_product = np.sum(x * self.weights[:len(x)])
            pred = np.mean(np.sin(dot_product))
            predictions.append(pred)

        predictions = np.array(predictions)
        # Inverse transform to get predictions in original scale
        predictions = self.output_scaler.inverse_transform(predictions.reshape(-1, 1)).flatten()
        return predictions