# WikiMap

WikiMap is a geospatial web application that brings Wikipedia articles to life on an interactive map. It allows users to explore history and knowledge based on location and time.

Completed as part of Advanced Web Mapping module for Tu Dublin.

## Features

*   **Interactive Map**: Visualize Wikipedia articles as points on a global map.
*   **Geospatial Search**: Automatically find articles near your current location or any search viewport.
*   **Time Travel**: Filter articles by year to uncover history from specific eras.
*   **Search**: Full-text search to find articles by title.
*   **User Accounts**: Secure login and signup via Email or **Google OAuth**.

## Technology Stack

*   **Backend**: Django 4.2 (Python)
*   **Database**: PostgreSQL + PostGIS (GeoDjango)
*   **Frontend**: HTML5, Tailwind CSS, JavaScript (Leaflet/OpenLayers for mapping)
*   **Containerization**: Docker & Docker Compose

## Deployment Guide

### Prerequisites

*   [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker Engine + Docker Compose installed.
*   Git

### Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/aidan-mcphee/Web_CA2.git
    cd Web_CA2
    ```

2.  **Environment Configuration**
    Create a `.env` file in the project root (same level as `docker-compose.yml`) if it doesn't exist. You can typically copy `.env.example`:
    ```bash
    cp .env.example .env
    ```
    Ensure it contains database credentials:
    ```env
    POSTGRES_DB=wikimap
    POSTGRES_USER=postgres
    POSTGRES_PASSWORD=postgres
    POSTGRES_HOST=db
    POSTGRES_PORT=5432
    ```

3.  **Build and Run**
    Use Docker Compose to build the containers and start the application:
    ```bash
    docker compose up -d --build
    ```
    *   This will start `db` (PostGIS), `web` (Django), `nginx`, and `pgadmin`.
    *   The app will be available at [http://localhost](http://localhost) (or `https://dev.amcp.ie` if configured).

4. **Wikipedia Data**
    Download the Wikipedia xml dump from [Wikimedia Torrent](https://academictorrents.com/download/1383d067a266af4a163f591531c9b64af458b107.torrent) and unzip into the `data` directory.
    Run the following command to import the data:
    ```bash
    python manage.py xmlparse data/enwiki-latest.xml
    ```
    this process will take a while, but the terminal will show progress. expect 25 million articles to be processed.

### Google Login Configuration

To enable "Sign in with Google":

1.  Obtain **Client ID** and **Client Secret** from the [Google Cloud Console](https://console.cloud.google.com/).
2.  Access the Django Admin at [http://localhost/admin/](http://localhost/admin/) (Default: `admin`/`admin`).
3.  Navigate to **Social Accounts** > **Social Applications**.
4.  Edit the **Google** application:
    *   **Client ID**: Paste your key.
    *   **Secret Key**: Paste your secret.
    *   **Sites**: Ensure your domain (e.g., `example.com` or `localhost`) is added to **Chosen sites**.

## Usage

*   **Home**: Landing page with quick access.
*   **Map**: The core experience. Zoom in to see clusters break apart into individual articles.
*   **Login/Signup**: Create an account to access personalized features (future-proofing).
