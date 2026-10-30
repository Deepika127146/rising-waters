import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GroupKFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

print("--- Testing ML Pipeline on flood_training_dataset_with_metadata.csv ---")

df = pd.read_csv('data/processed/flood_training_dataset_with_metadata.csv')
y = (df['FloodOccurred'] == 'Yes').astype(int)

# Features that are available before a flood (clean, no leakage)
clean_features = ['Region', 'Season', 'AnnualRainfall', 'SeasonalRainfall', 'Temperature']
X = df[clean_features].copy()

cat_cols = ['Region', 'Season']
num_cols = ['AnnualRainfall', 'SeasonalRainfall', 'Temperature']

# Preprocessor
preprocessor = ColumnTransformer([
    ('num', Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ]), num_cols),
    ('cat', Pipeline([
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('encoder', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ]), cat_cols)
])

# Stratified 80:20 Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

models = {
    'Decision Tree': DecisionTreeClassifier(random_state=42, max_depth=8),
    'Random Forest': RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42),
    'KNN': KNeighborsClassifier(n_neighbors=7),
    'XGBoost': XGBClassifier(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42, eval_metric='logloss')
}

print(f"Dataset size: {len(X)} rows. Train: {len(X_train)}, Test: {len(X_test)}")
print("\n--- Model Performance (80:20 Stratified Split - Clean Features) ---")
results = []
for name, clf in models.items():
    pipe = Pipeline([
        ('prep', preprocessor),
        ('model', clf)
    ])
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)
    y_prob = pipe.predict_proba(X_test)[:, 1] if hasattr(pipe, 'predict_proba') else y_pred
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)
    cm = confusion_matrix(y_test, y_pred)
    
    results.append({
        'Model': name,
        'Accuracy': acc,
        'Precision': prec,
        'Recall': rec,
        'F1-Score': f1,
        'ROC-AUC': auc,
        'TN': cm[0, 0], 'FP': cm[0, 1], 'FN': cm[1, 0], 'TP': cm[1, 1]
    })
    print(f"{name:15s} | Acc: {acc:.4f} | Prec: {prec:.4f} | Rec: {rec:.4f} | F1: {f1:.4f} | AUC: {auc:.4f} | CM: {cm.ravel()}")

res_df = pd.DataFrame(results)
print("\nSummary Table:")
print(res_df[['Model', 'Accuracy', 'Precision', 'Recall', 'F1-Score', 'ROC-AUC']])
