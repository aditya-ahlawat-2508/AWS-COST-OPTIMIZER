# ☁️ AWS Cost Optimizer

A **production-grade, teachable** AWS cost optimization dashboard built with Python. This project serves as a hands-on tutorial for integrating AWS SDKs, Streamlit, and AI-driven cost analysis into a single, cohesive web application.

| Layer | Technology |
|-------|-----------|
| Dashboard | Streamlit |
| AWS SDK | boto3 (Python) |
| AI Agent | LangChain + OpenAI GPT-4o |
| Infrastructure (Optional) | Terraform |
| Data Visualization | Plotly |

---

## 🚀 Quick Start Guide

Follow these instructions to get the project running on your local machine.

### 1. Prerequisites

Before you begin, ensure you have the following installed:
*   **Python 3.10+** (Required for Streamlit & LangChain)
*   **AWS CLI** (Must be installed and configured. Run `aws configure` in your terminal to set your local AWS credentials)
*   **OpenAI API Key** (Required for the AI Advisor feature)

### 2. Install Dependencies

Open your terminal, navigate to the project directory, and install the required Python packages:

```powershell
pip install -r requirements.txt
```

### 3. Environment Variables (The `.env` File)

The project relies on a `.env` file to securely load your API keys and configuration settings. 

**Instruction:** Create a new file in the root directory named exactly `.env` (with the dot in front) and copy-paste the template below into it.

```text
# ==========================================
# AWS Cost Optimizer — Environment Variables
# ==========================================

# 1. OpenAI API Key (Required for AI Advisor)
# Replace 'sk-...' with your actual OpenAI API key.
OPENAI_API_KEY=sk-your-openai-api-key-here

# 2. AWS Settings (Optional)
# By default, the app uses your machine's default AWS CLI profile.
# You only need to change this if you want to force a specific region.
AWS_REGION=us-east-1

# 3. Application Settings
# Change these to customize your dashboard's look and data pull.
APP_TITLE=AWS Cost Optimizer
COST_LOOKBACK_DAYS=30
```

*Note: Never commit your `.env` file to GitHub! The `.gitignore` file should ensure it stays local.*

### 4. Run the Dashboard

Once your `.env` file is saved and dependencies are installed, launch the app:

```powershell
streamlit run dashboard/app.py
```

Your browser will automatically open to `http://localhost:8501`.

---

## 📁 Project Structure & Architecture

This project is divided into distinct layers to separate infrastructure, backend logic, and frontend UI.

```text
Project -11 AWS Cost/
├── .env                          # ⚠️ You create this! (See above)
├── requirements.txt              # Python dependencies
├── PROJECT_SEQUENCE_GUIDE.md     # Tutorial guide on file creation order
├── config/
│   └── settings.py               # Loads .env variables for the app
├── lambda_/                      # Backend: AWS SDK interactions
│   ├── cost_explorer.py          # Fetches billing data
│   ├── services_inventory.py     # Lists running EC2, RDS, S3, etc.
│   └── service_actions.py        # Logic to stop/terminate resources
├── terraform/                    # Infrastructure: Deploying to AWS
│   ├── main.tf                   # Provisions Lambda & API Gateway
│   ├── variables.tf              # Terraform inputs
│   └── outputs.tf                # Terraform outputs
└── dashboard/                    # Frontend: Streamlit App
    ├── app.py                    # Main Home Page (Charts & Metrics)
    ├── pages/
    │   ├── 2_Services.py         # Resource management (Stop/Delete)
    │   └── 3_AI_Advisor.py       # AI Chat interface
    └── utils/
        ├── aws_client.py         # Bridge between UI and Lambda/Boto3
        ├── cost_utils.py         # UI formatting helpers
        └── ai_agent.py           # LangChain Tool & Agent definitions
```

---

## 📊 Dashboard Pages

1.  🏠 **Home (`app.py`)**: Displays your total AWS spend over the last 30 days (or custom range) with beautiful Plotly bar and line charts.
2.  🖥️ **Services (`2_Services.py`)**: A management hub. View all running EC2 instances, databases, and buckets. You can click to get instant AI advice on specific resources, or use the destructive buttons (Stop/Terminate) to manage them.
3.  🤖 **AI Advisor (`3_AI_Advisor.py`)**: A free-form chat interface. Ask the AI to analyze your entire AWS account and find cost-saving opportunities.

---

## 🤖 How the AI Advisor Works

The AI Advisor isn't just a generic chatbot; it has **tools**. We use LangChain to give GPT-4o the ability to securely query your real AWS environment.

When you ask, *"How can I save money?"*, the AI runs the following tools invisibly:
1.  `get_aws_cost_summary`: Reads your recent bill.
2.  `get_ec2_instances` / `get_rds_instances`: Looks for idle or oversized compute.
3.  `get_nat_gateways`: Checks for expensive, unused networking components.

It then synthesizes this actual data into actionable advice.

---

## ⚠️ Safety Warnings for the Tutorial

Because this dashboard connects to a real AWS account, the actions on the **Services** tab are live:
*   **Stop vs Terminate EC2**: Stopping is like shutting down a computer (can be restarted). Terminating deletes it forever.
*   **S3 Delete**: Deleting a bucket via the dashboard empties all files inside it first, then destroys the bucket. This is irreversible.
*   **Always read the confirmation prompts!**

---

## 🏗️ Terraform (Optional Remote Deployment)

While you can run this purely locally using your `aws configure` credentials, the `terraform/` folder contains exactly what you need to deploy the `lambda_/` Python code as a serverless AWS Lambda backend.

```powershell
cd terraform
terraform init
terraform apply
```

This will create an IAM Role, package your Python code, deploy the Lambda, and expose it via an API Gateway.
