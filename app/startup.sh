#!/bin/bash

# Start the Cloud SQL Auth Proxy in the background
/cloud_sql_proxy -dir=/cloudsql -instances=seminar-e2ee:me-west1:matrix-db=tcp:5432 &

# Wait a moment for the proxy to be ready
sleep 5

# Start your Streamlit app
streamlit run app.py --server.port=8080 --server.address=0.0.0.0
