# Quick Start Guide

Get up and running with the Comprehensive Modular AI/ML Platform in minutes.

## Installation (5 minutes)

### 1. Navigate to the project root
```bash
cd Project_1
```

### 2. Create and activate virtual environment
```bash
python3 -m venv streamlit_env
source streamlit_env/bin/activate  # Linux/Mac
# OR
streamlit_env\Scripts\activate     # Windows
```

### 3. Install dependencies
```bash
pip install -r ai_ml_tool/requirements.txt
```

### 4. Generate sample datasets (optional)
```bash
cd ai_ml_tool/sample_data
python3 generate_samples.py
cd ../..
```

## Launch the Application

From the project root:
```bash
streamlit run ai_ml_tool/app.py
```

Or use the provided script:
```bash
./run_app.sh
```

The app will open at `http://localhost:8501`

## Your First ML Workflow (10 minutes)

### Step 1: Load Data
1. Click on **Dataset Management**
2. Upload a CSV file (or use `sample_data/iris.csv`)
3. Click **Load Dataset**

### Step 2: Explore Data
1. Go to **Data Exploration**
2. View summary statistics
3. Check the correlation heatmap

### Step 3: Preprocess
1. Navigate to **Preprocessing**
2. **Missing Values Tab**: Choose strategy (e.g., "mean") and apply
3. **Feature Scaling Tab**: Select numeric columns, choose "standard", apply
4. **Train/Test Split Tab**: Select target column, adjust ratios, split

### Step 4: Train a Model
1. Go to **Model Training**
2. Select framework: **Scikit-Learn**
3. Choose model: **random_forest**
4. Adjust hyperparameters (e.g., number of trees: 100, max depth: 10)
5. Select task type: **classification** or **regression**
6. Click **Train Model**

> Models that only support one task type (e.g., Linear Regression = regression only, Logistic Regression = classification only) will show an error if paired with an incompatible task.

### Step 5: Save the Trained Model
1. After training completes, scroll to the **Save Trained Model** section on the Training page
2. Enter a save directory (defaults to `saved_models/`)
3. Click **Save Model**
4. Files are saved as `{model_name}_config.json` + `{model_name}_weights.{ext}`

### Step 6: Evaluate
1. Navigate to **Model Evaluation**
2. Select your trained model
3. Review metrics (accuracy, precision, recall, F1-score for classification; MSE, RMSE, MAE for regression)

### Step 7: Make Predictions
1. Go to **Prediction**
2. **Load a saved model**: Enter the save directory, pick a model from the dropdown, click **Load**
3. **Upload new data**: Upload a CSV file
4. **Select target column**: Choose which column is the output (actual values) — it will be excluded from model input and shown alongside predictions for comparison
5. Click **Generate Predictions**
6. Download results as CSV

## Example Workflows

### Classification (Iris Dataset)

```
1. Load iris.csv
2. Explore: Check correlation, distributions
3. Preprocess:
   - No missing values needed
   - Scale all features (standard)
   - Split: 70% train, 15% val, 15% test
   - Target: "target"
4. Train: Random Forest classifier
5. Save model from Training page
6. Evaluate: Check accuracy (should be ~95%+)
```

### Regression

```
1. Load regression_dataset.csv
2. Explore: Check for outliers
3. Outlier Detection:
   - Method: Isolation Forest
   - Contamination: 0.05
   - Remove outliers
4. Preprocess:
   - Scale features (minmax)
   - Split data (target: "target")
5. Train: Linear Regression
6. Evaluate: Check RMSE
```

### Deep Learning

```
1. Load classification_dataset.csv
2. Preprocess:
   - Handle missing values (mean)
   - Scale features (standard)
   - Encode if needed
   - Split data
3. Train:
   - Framework: Keras
   - Model: MLP
   - Hidden units: 64
   - Epochs: 20
   - Batch size: 32
4. Save model
5. View learning curves
6. Evaluate on test set
```

### Prediction with Saved Model

```
1. Go to Prediction page
2. Enter saved_models/ directory path
3. Select model from dropdown (e.g., "Random Forest (sklearn)")
4. Load model
5. Upload new CSV
6. Select target column for comparison
7. Generate predictions and download CSV
```

## Tips & Best Practices

### Data Quality
- Always explore data before training
- Handle missing values appropriately
- Check for outliers in regression tasks
- Normalize/standardize features

### Model Selection
- Start simple (Linear/Logistic Regression)
- Try ensemble methods (Random Forest, Extra Trees)
- Use deep learning for complex patterns
- Compare multiple models on the same preprocessed data

### Training
- Start with default hyperparameters
- Use validation set to tune
- Watch for overfitting (train vs val metrics)
- Increase epochs gradually for deep learning models

### Saving & Loading
- Save models from either the Training page or the Prediction page
- Multiple models can coexist in the same directory (files are prefixed with model name)
- When loading, browse the directory and pick the specific model from the dropdown

### Evaluation
- Don't just look at accuracy
- Check precision/recall for imbalanced data
- Use confusion matrix for classification
- Plot learning curves to diagnose issues

## Common Pipelines

### Quick Classification
```
Dataset -> Explore -> Scale -> Split -> Random Forest -> Evaluate -> Save
```

### Regression with Outliers
```
Dataset -> Outlier Detection -> Remove -> Scale -> Split ->
Linear Regression -> Evaluate -> Save
```

### Deep Learning Pipeline
```
Dataset -> Explore -> Preprocess -> Encode -> Scale -> Split ->
Keras MLP -> Learning Curves -> Evaluate -> Save
```

### Model Comparison
```
Same preprocessed data ->
  Train Random Forest
  Train SVM
  Train MLP (Keras)
  Train LSTM (PyTorch)
-> Compare metrics -> Select best -> Save
```

## Keyboard Shortcuts

- `Ctrl+R` - Rerun the app
- `Ctrl+C` - Stop the server (in terminal)

## Next Steps

1. Try all sample datasets
2. Upload your own data
3. Experiment with different models and frameworks
4. Compare model performance
5. Save your best models
6. Load saved models and predict on new data

## Need Help?

- Check [README.md](README.md) for detailed documentation
- Examine sample datasets in `sample_data/`
