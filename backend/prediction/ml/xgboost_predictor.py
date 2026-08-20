import xgboost as xgb
import numpy as np

class XGBoostPredictor:
    def __init__(self, n_estimators=200, max_depth=4, learning_rate=0.05, random_state=42):
        self.model = xgb.XGBRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=random_state,
            objective='reg:squarederror'
        )
        self.feature_cols = None
        
    def _extract_features(self, df, target_col='invocations'):
        # Exclude non-feature columns
        exclude = {target_col, 'timestamp', 'function'}
        # Also ensure we only take numeric columns
        numeric_df = df.select_dtypes(include=[np.number])
        features = [c for c in numeric_df.columns if c not in exclude]
        return features

    def fit(self, train_df, target_col='invocations'):
        self.feature_cols = self._extract_features(train_df, target_col)
        
        X = train_df[self.feature_cols].values
        y = train_df[target_col].values
        
        self.model.fit(X, y)
        return self
        
    def predict(self, test_df):
        if self.feature_cols is None:
            raise ValueError("Model not fitted")
            
        X = test_df[self.feature_cols].values
        return self.model.predict(X)
