# Learn: https://github.com/Qiskit/textbook/blob/main/notebooks/quantum-machine-learning/training.ipynb

# Gradients
"""First, we need to define our parameterized state, which 
 is the Qiskit RealAmplitudes circuit on two qubits:"""

from qiskit.circuit.library import RealAmplitudes
import matplotlib.pyplot as plt
ansatz = RealAmplitudes(num_qubits=3, reps=2, entanglement='linear').decompose()
ansatz.draw('mpl')
plt.show()