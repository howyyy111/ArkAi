# Introduction to Machine Learning

Machine Learning (ML) is a subset of artificial intelligence (AI) that focuses on building systems that learn from data, rather than being explicitly programmed.

## 1. Types of Machine Learning

There are three primary categories of machine learning:

### Supervised Learning
The model is trained on a labeled dataset, meaning that each training example is paired with an output label. 
* **Goal:** Predict the output for new, unseen data.
* **Examples:** Linear Regression (predicting continuous values like house prices), Logistic Regression (classifying data like spam vs. not spam).

### Unsupervised Learning
The model is provided with unlabeled data and must find patterns, structures, or relationships within it.
* **Goal:** Discover hidden patterns in the data.
* **Examples:** K-Means Clustering (grouping customers based on purchasing behavior), Principal Component Analysis (dimensionality reduction).

### Reinforcement Learning
An agent learns to make decisions by performing actions in an environment and receiving rewards or penalties.
* **Goal:** Learn a policy that maximizes the total cumulative reward.
* **Examples:** AlphaGo, training a robot to walk.

## 2. The Machine Learning Pipeline

A typical ML project follows these steps:
1. **Data Collection:** Gathering the necessary raw data.
2. **Data Preprocessing:** Cleaning the data, handling missing values, and scaling features.
3. **Feature Engineering:** Creating new features or selecting the most important ones.
4. **Model Selection:** Choosing an appropriate algorithm (e.g., Random Forest, Neural Network).
5. **Training:** Feeding the data into the model so it can learn the patterns.
6. **Evaluation:** Testing the model on a separate dataset (test set) using metrics like Accuracy, Precision, Recall, or Mean Squared Error (MSE).
7. **Deployment:** Integrating the trained model into a production environment.
8. **Monitoring:** Continuously tracking the model's performance to detect data drift.

## 3. Overfitting and Underfitting

* **Overfitting:** The model learns the training data too well, including the noise, and performs poorly on unseen data (high variance). *Solution:* Use more data, regularize the model, or simplify the architecture.
* **Underfitting:** The model is too simple to capture the underlying patterns in the data (high bias). *Solution:* Use a more complex model, add more features, or train longer.
