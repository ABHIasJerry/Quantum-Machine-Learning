import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Hashable
import warnings
warnings.filterwarnings("ignore")

class DatasetAnalyzer:
    """
    Automatically extract and analyze dataset details from CSV files.
    """

    def __init__(self, csv_path: str):
        """
        Initialize the analyzer with a CSV file.

        Args:
            csv_path: Path to the CSV file
        """
        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path)
        self.details = {}

    def extract_all_details(self) -> Dict[str, Any]:
        """
        Extract all dataset details.

        Returns:
            Dictionary containing all extracted information
        """
        self.details = {
            'file_path': self.csv_path,
            'shape': self._get_shape(),
            'feature_names': self._get_feature_names(),
            'feature_dtypes': self._get_feature_dtypes(),
            'statistics': self._get_statistics(),
            'missing_values': self._get_missing_values(),
            'numeric_features': self._get_numeric_features(),
            'categorical_features': self._get_categorical_features(),
            'feature_ranges': self._get_feature_ranges(),
            'memory_usage': self._get_memory_usage(),
            'correlation_matrix': self._get_correlation_matrix(),
            'summary': self._get_summary()
        }
        return self.details

    def _get_shape(self) -> Tuple[int, int]:
        """Get dataset shape (rows, columns)"""
        return self.df.shape

    def _get_feature_names(self) -> List[str]:
        """Get all feature names"""
        return self.df.columns.tolist()

    def _get_feature_dtypes(self) -> Dict[str, str]:
        """Get data type for each feature"""
        return self.df.dtypes.astype(str).to_dict()

    def _get_statistics(self) -> Dict[str, Dict[str, float]]:
        """Get statistical summary for numeric features"""
        return self.df.describe().to_dict()

    def _get_missing_values(self) -> Dict[str, int]:
        """Get count of missing values per feature"""
        missing = self.df.isnull().sum()
        return missing[missing > 0].to_dict()

    def _get_numeric_features(self) -> List[str]:
        """Get list of numeric features"""
        return self.df.select_dtypes(include=[np.number]).columns.tolist()

    def _get_categorical_features(self) -> List[str]:
        """Get list of categorical features"""
        return self.df.select_dtypes(include=['object']).columns.tolist()

    def _get_feature_ranges(self) -> Dict[str, Dict[str, Any]]:
        """Get min and max values for numeric features"""
        ranges = {}
        for col in self._get_numeric_features():
            ranges[col] = {
                'min': float(self.df[col].min()),
                'max': float(self.df[col].max()),
                'range': float(self.df[col].max() - self.df[col].min())
            }
        return ranges

    def _get_memory_usage(self) -> dict[str, dict[Hashable, str] | Any]:
        """Get memory usage information"""
        total_memory = self.df.memory_usage(deep=True).sum() / 1024 ** 2  # Convert to MB
        return {
            'total_memory_mb': round(total_memory, 2),
            'per_feature': {col: f"{size / 1024:.2f} KB"
                            for col, size in self.df.memory_usage(deep=True).items()}
        }

    def _get_correlation_matrix(self) -> Dict:
        """Get correlation matrix for numeric features"""
        numeric_df = self.df.select_dtypes(include=[np.number])
        if len(numeric_df.columns) > 1:
            return numeric_df.corr().to_dict()
        return {}

    def _get_summary(self) -> Dict[str, Any]:
        """Get high-level summary"""
        return {
            'total_rows': int(self.df.shape[0]),
            'total_columns': int(self.df.shape[1]),
            'numeric_features_count': len(self._get_numeric_features()),
            'categorical_features_count': len(self._get_categorical_features()),
            'missing_values_count': int(self.df.isnull().sum().sum()),
            'duplicate_rows': int(self.df.duplicated().sum())
        }

    def print_summary(self):
        """Print a formatted summary of dataset details"""
        if not self.details:
            self.extract_all_details()

        summary = self.details['summary']
        print("\n" + "=" * 60)
        print("DATASET SUMMARY")
        print("=" * 60)
        print(f"File: {self.csv_path}")
        print(f"Shape: {summary['total_rows']} rows × {summary['total_columns']} columns")
        print(f"Numeric Features: {summary['numeric_features_count']}")
        print(f"Categorical Features: {summary['categorical_features_count']}")
        print(f"Missing Values: {summary['missing_values_count']}")
        print(f"Duplicate Rows: {summary['duplicate_rows']}")
        print(f"Memory Usage: {self.details['memory_usage']['total_memory_mb']} MB")

        print("\n" + "=" * 60)
        print("FEATURE DETAILS")
        print("=" * 60)
        for feature, dtype in self.details['feature_dtypes'].items():
            print(f"{feature:20} | Type: {dtype:15}", end="")
            if feature in self.details['feature_ranges']:
                frange = self.details['feature_ranges'][feature]
                print(f" | Range: [{frange['min']:.2f}, {frange['max']:.2f}]")
            else:
                print()

        if self.details['missing_values']:
            print("\n" + "=" * 60)
            print("MISSING VALUES")
            print("=" * 60)
            for feature, count in self.details['missing_values'].items():
                pct = (count / summary['total_rows']) * 100
                print(f"{feature:20} | Count: {count:5} ({pct:.2f}%)")

    def to_dict(self) -> Dict[str, Any]:
        """Return all details as dictionary"""
        if not self.details:
            self.extract_all_details()
        return self.details

    def to_json(self, output_path: str):
        """Save details to JSON file"""
        import json
        if not self.details:
            self.extract_all_details()

        # Convert numpy types to JSON serializable types
        details_json = json.dumps(self.details, default=str, indent=4)
        with open(output_path, 'w') as f:
            f.write(details_json)
        print(f"Details saved to {output_path}")