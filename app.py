from flask import Flask, render_template, request
import numpy as np
import pickle
from sklearn.preprocessing import LabelEncoder, StandardScaler

app = Flask(__name__)

# Initialize default encoders with ALL expected categories
default_encoders = {
    'gender': LabelEncoder().fit(['m', 'f', 'other']),
    'ethnicity': LabelEncoder().fit(['White-European', 'Middle Eastern', 'Asian', 
                                   'Black', 'South Asian', 'Hispanic', 'Pasifika', 
                                   'Others', '?']),
    'jaundice': LabelEncoder().fit(['no', 'yes']),
    'austim': LabelEncoder().fit(['no', 'yes']),
    'used_app_before': LabelEncoder().fit(['no', 'yes']),
    'country': LabelEncoder().fit(['Unknown', 'United States', 'India', 'United Kingdom',
                                 'Australia', 'Canada', 'Other']),
    'relation': LabelEncoder().fit(['Self', 'Parent', 'Caregiver', 'Other']),
    'age_scaler': StandardScaler().fit(np.array([[4], [100]]))  # Age range 4-100
}

# Try loading existing encoders or create new ones
try:
    with open('encoders.pkl', 'rb') as f:
        encoders = pickle.load(f)
        
        # Ensure all required encoders exist
        for key in default_encoders:
            if key not in encoders:
                print(f"Adding missing encoder: {key}")
                encoders[key] = default_encoders[key]
        
        # Save updated encoders
        with open('encoders.pkl', 'wb') as f:
            pickle.dump(encoders, f)
            
except Exception as e:
    print(f"Creating new encoders file: {e}")
    encoders = default_encoders
    with open('encoders.pkl', 'wb') as f:
        pickle.dump(encoders, f)

# Load model and handle feature count
with open('best_model.pkl', 'rb') as f:
    model = pickle.load(f)
    # Handle different sklearn versions
    expected_features = getattr(model, 'n_features_in_', 
                              getattr(model, 'n_features_', 19))  # Fallback to 19

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        try:
            # 1. Collect all 19 features from form
            raw_input = {
                # AQ-10 Scores (10 features)
                'A1_Score': int(request.form.get('A1_Score', 0)),
                'A2_Score': int(request.form.get('A2_Score', 0)),
                'A3_Score': int(request.form.get('A3_Score', 0)),
                'A4_Score': int(request.form.get('A4_Score', 0)),
                'A5_Score': int(request.form.get('A5_Score', 0)),
                'A6_Score': int(request.form.get('A6_Score', 0)),
                'A7_Score': int(request.form.get('A7_Score', 0)),
                'A8_Score': int(request.form.get('A8_Score', 0)),
                'A9_Score': int(request.form.get('A9_Score', 0)),
                'A10_Score': int(request.form.get('A10_Score', 0)),
                
                # Demographic info (9 features)
                'age': max(4, min(120, float(request.form.get('age', 30.0)))),
                'gender': request.form.get('gender', 'm'),
                'ethnicity': request.form.get('ethnicity', '?'),
                'jaundice': request.form.get('jaundice', 'no'),
                'austim': request.form.get('austim', 'no'),
                'country': request.form.get('country', 'Unknown'),
                'relation': request.form.get('relation', 'Self'),
                'result': float(request.form.get('result', 0.0)),
                'used_app_before': request.form.get('used_app_before', 'no')
            }

            # 2. Preprocess all features
            processed = np.array([
                # AQ-10 Scores
                raw_input['A1_Score'], raw_input['A2_Score'], raw_input['A3_Score'],
                raw_input['A4_Score'], raw_input['A5_Score'], raw_input['A6_Score'],
                raw_input['A7_Score'], raw_input['A8_Score'], raw_input['A9_Score'],
                raw_input['A10_Score'],
                
                # Demographic features
                encoders['age_scaler'].transform([[raw_input['age']]])[0][0],
                encoders['gender'].transform([raw_input['gender']])[0],
                encoders['ethnicity'].transform([raw_input['ethnicity']])[0],
                encoders['jaundice'].transform([raw_input['jaundice']])[0],
                encoders['austim'].transform([raw_input['austim']])[0],
                encoders['country'].transform([raw_input['country']])[0],
                encoders['relation'].transform([raw_input['relation']])[0],
                raw_input['result'],
                encoders['used_app_before'].transform([raw_input['used_app_before']])[0]
            ]).reshape(1, -1)

            # 3. Verify feature count
            if processed.shape[1] != expected_features:
                raise ValueError(f"Expected {expected_features} features, got {processed.shape[1]}")
            
            # 4. Predict
            proba = model.predict_proba(processed)[0][1]
            
            return render_template(
                'index.html',
                prediction="ASD Likely" if proba >= 0.5 else "ASD Unlikely",
                confidence=f"{proba*100:.1f}%",
                show_result=True
            )
            
        except Exception as e:
            return render_template('index.html', 
                                error=f"Processing error: {str(e)}",
                                show_result=False)

    return render_template('index.html', show_result=False)

if __name__ == '__main__':
    app.run(debug=True)