# Vox Populi Platform

Final Year B.Sc. Project in Data Engineering, Ben-Gurion University.

## Overview

Surveys have long been a vital tool in fields such as marketing, healthcare, education, and public opinion research. While their evolution—from door-to-door interviews to digital polls—has made data collection faster and more scalable, it has also introduced new challenges: unreliable responses, outdated information, and low engagement rates.

The Vox Populi Platform is designed to revolutionize how we conduct surveys by tapping into real-time, user-consented messaging data. Leveraging end-to-end encryption (E2EE), instant messaging integrations, and advanced anonymization techniques, VP empowers researchers to gather high-quality, real-world insights—without compromising user privacy.

## Key Features

- Cross-Platform Messaging Integration with WhatsApp, Telegram, and Signal.

- Real-Time Data Feed to continuously collect chat data from participants' chosen conversations.

- Smart Anonymization with built-in Hebrew support and NLP-based and LLM anonymization tools.

- Management Dashboard for an intuitive user experience to monitor data streams and participants.

## Why VPP?

Unlike traditional surveys, our platform allows:

- Real-time engagement with diverse and dynamic audiences.

- Passive, yet consensual, data collection to improve accuracy.

- Deep integration with encrypted protocols like Matrix.

- Seamless support for Hebrew, including Hebrew-specific anonymization using LLMs.

## Technologies Used

- Matrix Protocol for secure and decentralized messaging integration.

- NER Models, Regex, and LLM for anonymization.

- Custom Dashboard for full user control and visualization.

- Cloud Database for managing continuous data streams.

## Use Cases

- Academic research with real-world chat data.

- Sentiment analysis from anonymous conversations.

- Real-time opinion polling without traditional survey fatigue.

## Project Structure Overview

The project contains the following key files:

### Core Application Files
- **`app.py`** - Main entry point for the application
- **`user_app.py`** - User-facing dashboard and functionality
- **`researcher_app.py`** - Tools and features for researchers

### Backend Components
- **`connectors.py`** - Handles connections to GCP storage and Cloud SQL for external resource interaction
- **`dbs.py`** - Manages database queries and operations for data retrieval and manipulation
- **`m_monitor.py`** - Core logic for Matrix server interaction, bridging WhatsApp, Signal, and Telegram
- **`web_monitor.py`** - Wrapper for m_monitor.py, integrating Matrix functionality into the web application

### Configuration & Deployment
- **`requirements.txt`** - Lists all project dependencies for reproducibility
- **`.streamlit/config.toml`** - Configures Streamlit application settings
- **`Dockerfile`** - Containerization configuration for deployment
- **`startup.sh`** - Automates GCP startup process including database proxy setup and app launch


## Setup Instructions

### 1. Clone the Repository

First, download or clone the repository to your local machine:

```bash
git clone https://github.com/ronshrb/VoxPopuliPlatform.git
cd VoxPopuliPlatform
```

### 2. Set up Environment Variables

Create a `.env` file in the `app` folder (`app/.env`) with the following variables:

```env
# Database Configuration
users_db_user=your_database_username
users_db_pass=your_database_password
db_name=your_database_name

# Matrix Configuration
matrix-db-connection-string=your_matrix_db_connection_string
SYNAPSE_URL=your_matrix_synapse_url
ADMIN_ACCESS_TOKEN=your_admin_access_token

# Bot Configuration
WHATSAPP_BOT_MXID=@whatsapp_bot:your_server.com
SIGNAL_BOT_MXID=@signal_bot:your_server.com
TELEGRAM_BOT_MXID=@telegram_bot:your_server.com

# Server Configuration
SERVER=your_server_url
BUCKET_NAME=your_message_storage_bucket
```

**⚠️ Security Note:** Make sure the `.env` file is included in your `.gitignore` to prevent sensitive credentials from being committed to version control.

### 3. Install Dependencies

Use python 3.11 and install the required Python packages:

```bash
pip install -r requirements.txt
```

### 4. Run the Application

#### Local Development

```bash
streamlit run app/app.py
```

#### Cloud Deployment

1. **Connect Cloud Run to your repository**
   - Link your repository to your cloud provider
   
2. **Configure deployment settings**
   - Select the correct branch
   - Set the Dockerfile path to `app/Dockerfile` (or `app/docker/Dockerfile` if in subdirectory)
   
3. **Set up environment variables**
   - Add all the variables from your `.env` file as secrets/environment variables in your cloud platform
   
4. **Configure service account permissions**
   - Grant the service account the following roles:
     - Storage bucket read permissions
     - Cloud SQL management permissions

### Troubleshooting

- Ensure Python version compatibility with your requirements
- Verify all environment variables are properly set
- Check that database connections are accessible from your deployment environment
- Confirm service account has sufficient permissions for cloud resources

### Next Steps

After successful deployment, verify the application is running correctly by accessing the provided URL and testing core functionality.