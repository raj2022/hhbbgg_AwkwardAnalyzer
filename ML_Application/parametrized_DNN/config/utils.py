import os 
import pandas as pd
import uproot
import numpy as np

from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

def load_data(file_paths, columns):
    """
    Load data from ROOT files into a Pandas Dataframe.
    
    Args:
        file_paths (list of tuples): List of (file_path, key) pairs.
        columns (list): List of columns to load.
    
    Returns:
        dict: A dictionary of DataFrames keyed by ROOT tree names.
    
    """
    dataframes = {}
    for file, key in file_paths:
        try:
            with uproot.open(file) as f:
                dataframes[key] = f[key].arrays(columns, library="pd")
        except:
            print(f"Error loading {file} with key {key}: {e}")
    return dataframes


def combine_dataframes(dataframes, include_keys):
    """
    
    Combine DataFrames based on specified keys.

    Args:
        dataframes (dict): Dictionary of DataFrames.
        include_keys (list): Keys to include in the combination.

    Returns:
        pd.DataFrame: Combined DataFrame.
    """
    filtered_dfs = [dataframes[key] for key in dataframes if any(k in key for k in include_keys)]
    return pd.concat(filtered_dfs, ignore_index=True)

def preprocess_data(df, label=None):
    """
    Preprocess data by handling missing values and scaling features.

    Args:
        df (pd.DataFrame): Input DataFrame.
        label (int, optional): Label to assign to the data. Defaults to None.

    Returns:
        pd.DataFrame: Preprocessed DataFrame.
    """
    if label is not None:
        df['label'] = label

    # Handle missing values
    imputer = SimpleImputer(strategy='mean')
    df[df.columns] = imputer.fit_transform(df)

    # Scale data
    scaler = StandardScaler()
    df[df.columns] = scaler.fit_transform(df)

    return df

def split_data(signal_df, background_df, test_size=0.2):
    """
    Split data into training and testing sets.

    Args:
        signal_df (pd.DataFrame): Signal data.
        background_df (pd.DataFrame): Background data.
        test_size (float): Proportion of test data.

    Returns:
        tuple: Train and test sets (X_train, X_test, y_train, y_test).
    """
    from sklearn.model_selection import train_test_split

    # Combine data
    data = pd.concat([signal_df, background_df], ignore_index=True)
    X = data.drop(columns=['label'])
    y = data['label']

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)

    return X_train, X_test, y_train, y_test


                
    