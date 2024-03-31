# Reading Speed and Skill Improvement App Backend API

This backend API is designed to support VistaRead, an app that measures and improves reading speed and skill.

## Setup

1. Install the required packages by running `pip install -r requirements.txt`.
2. Create a Firebase project and download the service account key as `key.json`.
3. Initialize the Firebase Admin SDK with the service account key.

## API Endpoints

### Register

- **URL:** `/register`
- **Method:** `POST`
- **Description:** Registers a new user with email and password.
- **Parameters:**
  - `email`: User's email address.
  - `password`: User's password.
- **Response:** JSON containing the registered user's email.

### Sign In

- **URL:** `/signin`
- **Method:** `POST`
- **Description:** Signs in a user with email and password.
- **Parameters:**
  - `email`: User's email address.
  - `password`: User's password.
- **Response:** JSON containing the user's session ID.

### Generate Paragraph

- **URL:** `/generate_paragraph`
- **Method:** `GET`
- **Description:** Retrieves a random paragraph for the user to read.
- **Response:** JSON containing the paragraph text.

### Get All Paragraphs

- **URL:** `/get_all_paragraphs`
- **Method:** `GET`
- **Description:** Retrieves all paragraphs available in the database.
- **Response:** JSON array containing paragraph objects.

### Get Response

- **URL:** `/get_response`
- **Method:** `POST`
- **Description:** Retrieves a user's response to a paragraph.
- **Parameters:**
  - `id`: Paragraph ID.
  - `sessionID`: User's session ID.
- **Response:** JSON containing the user's response.

### Analyze

- **URL:** `/analyze`
- **Method:** `POST`
- **Description:** Analyzes a user's summary of a paragraph.
- **Parameters:**
  - `summary`: User's summary of the paragraph.
  - `textReadID`: ID of the paragraph being summarized.
  - `readDuration`: Duration of time spent reading the paragraph.
  - `sessionID`: User's session ID.
- **Response:** JSON containing the analysis results.

### Add Text

- **URL:** `/addText`
- **Method:** `POST`
- **Description:** Adds a new text passage to the database.
- **Parameters:**
  - `text`: The text passage.
  - `topic`: The topic of the text passage.
  - `title`: The title of the text passage.
- **Response:** JSON indicating that the text passage has been added.

## Technologies Used

- Flask: Web framework for handling API requests.
- Firebase: Used for user authentication and data storage.
- Flask Bcrypt: Used for password hashing.
- Google Cloud Firestore: Database for storing text passages and user responses.
- Requests: Used for making HTTP requests to external services.
